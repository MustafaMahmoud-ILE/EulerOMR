"""Statistical engine: mean, median, mode, stddev; per-version; question-level diagnostics; fairness."""
from __future__ import annotations
import statistics
import math
from dataclasses import dataclass, field
from euler_omr.models.scan_result import GradeRecord
from euler_omr.models.answer_key import AnswerKey
from euler_omr.constants import EASY_THRESHOLD, MODERATE_THRESHOLD, CONFUSION_THRESHOLD, FAIRNESS_THRESHOLD


@dataclass
class QuestionAnalysis:
    question_idx: int
    version: str
    option_frequencies: dict[str, int] = field(default_factory=dict)
    total_responses: int = 0
    correct_count: int = 0
    difficulty_index: float = 0.0
    difficulty_class: str = "MODERATE"
    is_confusing: bool = False


@dataclass
class QuestionChoiceOverall:
    """Answer choice frequencies for a question across ALL students."""
    question_idx: int
    option_frequencies: dict[str, int] = field(default_factory=dict)
    total_responses: int = 0
    correct_keys: list[str] = field(default_factory=list)


@dataclass
class QuestionChoiceByVersion:
    """Answer choice percentages for a question broken down by version."""
    question_idx: int
    # {version: {option: percentage}}
    version_option_pct: dict[str, dict[str, float]] = field(default_factory=dict)
    # {version: list of correct options}
    version_correct_keys: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class VersionStats:
    version: str
    count: int = 0
    mean: float = 0.0
    median: float = 0.0
    mode: float = 0.0
    stddev: float = 0.0
    min_score: float = 0.0
    max_score_val: float = 0.0
    scores: list[float] = field(default_factory=list)


@dataclass
class VersionRankEntry:
    version: str
    mean: float
    difficulty_label: str = "Moderate"


@dataclass
class VersionOutlier:
    version: str
    mean: float
    z_score: float
    label: str = ""


@dataclass
class ScoreDistEntry:
    score: float
    count: int
    percentage: float


@dataclass
class ItemPsychometrics:
    question_idx: int
    correct_keys: list[str] = field(default_factory=list)
    p_value: float = 0.0  # item difficulty: proportion correct
    discrimination_index: float = 0.0  # D = P_High - P_Low
    failure_rate: float = 0.0  # 1 - p_value
    point_biserial: float = 0.0
    corrected_item_total: float = 0.0
    distractor_efficiency: float = 0.0
    quality_class: str = "Acceptable"


@dataclass
class AnalysisReport:
    overall_mean: float = 0.0
    overall_median: float = 0.0
    overall_mode: float = 0.0
    overall_stddev: float = 0.0
    overall_min: float = 0.0
    overall_max: float = 0.0
    overall_scores: list[float] = field(default_factory=list)
    score_distribution: list[ScoreDistEntry] = field(default_factory=list)
    version_stats: list[VersionStats] = field(default_factory=list)
    question_analyses: list[QuestionAnalysis] = field(default_factory=list)
    question_choices_overall: list[QuestionChoiceOverall] = field(default_factory=list)
    question_choices_by_version: list[QuestionChoiceByVersion] = field(default_factory=list)
    item_psychometrics: list[ItemPsychometrics] = field(default_factory=list)
    fairness_verdict: str = "FAIR"
    fairness_explanation: str = ""
    version_ranking: list[VersionRankEntry] = field(default_factory=list)
    version_outliers: list[VersionOutlier] = field(default_factory=list)
    anova_f: float = 0.0
    anova_p: float = 1.0
    kruskal_h: float = 0.0
    kruskal_p: float = 1.0
    grand_mean_versions: float = 0.0
    std_version_means: float = 0.0
    max_score: float = 0.0
    total_students: int = 0
    active_options: list[str] = field(default_factory=list)
    cronbach_alpha: float = 0.0
    kr20: float = 0.0
    split_half_reliability: float = 0.0
    topic_analyses: list[dict] = field(default_factory=list)
    student_analytics: list[dict] = field(default_factory=list)
    tukey_hsd_results: list[dict] = field(default_factory=list)
    inter_item_correlation: list[list[float]] = field(default_factory=list)
    equated_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    at_risk_students: list[dict] = field(default_factory=list)



class AnalysisEngine:
    @staticmethod
    def _safe_mode(values):
        try:
            return statistics.mode(values)
        except statistics.StatisticsError:
            return values[0] if values else 0

    @staticmethod
    def _safe_multimode(values):
        try:
            return statistics.multimode(values)
        except Exception:
            return [values[0]] if values else [0]

    @staticmethod
    def _safe_stddev(values):
        return statistics.stdev(values) if len(values) > 1 else 0.0

    @staticmethod
    def _anova_oneway(groups: list[list[float]]):
        """Simple one-way ANOVA F-test (no scipy dependency)."""
        all_vals = [v for g in groups for v in g]
        if not all_vals or len(groups) < 2:
            return 0.0, 1.0
        grand_mean = sum(all_vals) / len(all_vals)
        k = len(groups)
        n_total = len(all_vals)

        ss_between = sum(len(g) * (sum(g)/len(g) - grand_mean)**2 for g in groups if g)
        ss_within = sum((v - sum(g)/len(g))**2 for g in groups if g for v in g)

        df_between = k - 1
        df_within = n_total - k

        if df_between <= 0 or df_within <= 0 or ss_within == 0:
            return 0.0, 1.0

        ms_between = ss_between / df_between
        ms_within = ss_within / df_within
        f_stat = ms_between / ms_within

        # Approximate p-value using F-distribution (rough approximation)
        p_value = AnalysisEngine._f_pvalue_approx(f_stat, df_between, df_within)
        return round(f_stat, 4), round(p_value, 6)

    @staticmethod
    def _f_pvalue_approx(f_stat, df1, df2):
        """Very rough p-value approximation for F distribution."""
        try:
            from scipy.stats import f as f_dist
            return float(1 - f_dist.cdf(f_stat, df1, df2))
        except ImportError:
            if f_stat > 10:
                return 0.0001
            elif f_stat > 5:
                return 0.001
            elif f_stat > 3:
                return 0.01
            elif f_stat > 2:
                return 0.05
            else:
                return 0.2

    @staticmethod
    def _kruskal_wallis(groups: list[list[float]]):
        """Simple Kruskal-Wallis H test."""
        try:
            from scipy.stats import kruskal
            valid = [g for g in groups if len(g) >= 2]
            if len(valid) < 2:
                return 0.0, 1.0
            h, p = kruskal(*valid)
            return round(float(h), 4), round(float(p), 6)
        except ImportError:
            return 0.0, 1.0
        except Exception:
            return 0.0, 1.0

    @staticmethod
    def _tukey_hsd(groups: list[list[float]], versions: list[str]) -> list[dict]:
        """Runs Tukey HSD post-hoc test to identify significantly differing versions."""
        results = []
        if len(groups) < 2:
            return results
        try:
            from scipy.stats import tukey_hsd
            res = tukey_hsd(*groups)
            n = len(groups)
            for i in range(n):
                for j in range(i + 1, n):
                    p_val = res.pvalue[i, j]
                    diff = res.statistic[i, j]
                    if p_val < 0.05:
                        results.append({
                            "pair": f"Version {versions[i]} vs Version {versions[j]}",
                            "diff": round(float(diff), 3),
                            "p_value": round(float(p_val), 4)
                        })
        except Exception:
            pass
        return results

    @staticmethod
    def analyze(grades: list[GradeRecord], answer_key: AnswerKey, active_questions: int) -> AnalysisReport:
        report = AnalysisReport()
        if not grades:
            return report

        report.total_students = len(grades)
        report.max_score = grades[0].max_score if grades else active_questions
        all_scores = [g.score for g in grades]
        report.overall_scores = all_scores
        report.overall_mean = round(statistics.mean(all_scores), 3)
        report.overall_median = round(statistics.median(all_scores), 1)
        report.overall_mode = AnalysisEngine._safe_mode(all_scores)
        report.overall_stddev = round(AnalysisEngine._safe_stddev(all_scores), 3)
        report.overall_min = min(all_scores)
        report.overall_max = max(all_scores)

        # Collect unique active options from the data
        all_options = set()
        for g in grades:
            for a in g.answers:
                if a:
                    all_options.add(a)
        report.active_options = sorted(all_options)

        # Score distribution
        unique_scores = sorted(list(set(all_scores)))
        for s in unique_scores:
            cnt = all_scores.count(s)
            pct = round(cnt / len(all_scores) * 100, 1)
            report.score_distribution.append(ScoreDistEntry(score=s, count=cnt, percentage=pct))

        # Per-version stats
        by_version: dict[str, list[GradeRecord]] = {}
        for g in grades:
            by_version.setdefault(g.version, []).append(g)

        for ver, ver_grades in sorted(by_version.items()):
            scores = [g.score for g in ver_grades]
            modes = AnalysisEngine._safe_multimode(scores)
            vs = VersionStats(
                version=ver, count=len(scores),
                mean=round(statistics.mean(scores), 3),
                median=round(statistics.median(scores), 1),
                mode=modes[0] if len(modes) == 1 else modes[0],
                stddev=round(AnalysisEngine._safe_stddev(scores), 3),
                min_score=min(scores),
                max_score_val=max(scores),
                scores=scores,
            )
            report.version_stats.append(vs)

        # Question-level analysis (per version)
        for ver, ver_grades in sorted(by_version.items()):
            ver_keys = answer_key.get_version_keys(ver)
            for q_idx in range(active_questions):
                freq: dict[str, int] = {}
                correct_count = 0
                total = 0
                correct_opts = ver_keys.get(q_idx, set())
                for g in ver_grades:
                    ans = g.answers[q_idx] if q_idx < len(g.answers) else ""
                    key = ans if ans else "BLANK"
                    freq[key] = freq.get(key, 0) + 1
                    total += 1
                    if ans in correct_opts:
                        correct_count += 1
                p = correct_count / total if total > 0 else 0
                if p > EASY_THRESHOLD:
                    dc = "EASY"
                elif p >= MODERATE_THRESHOLD:
                    dc = "MODERATE"
                else:
                    dc = "HARD"
                max_freq_ratio = max(freq.values()) / total if total > 0 and freq else 0
                qa = QuestionAnalysis(
                    question_idx=q_idx, version=ver,
                    option_frequencies=freq, total_responses=total,
                    correct_count=correct_count, difficulty_index=round(p, 3),
                    difficulty_class=dc, is_confusing=max_freq_ratio < CONFUSION_THRESHOLD,
                )
                report.question_analyses.append(qa)

        # Question choice analysis - ALL students
        for q_idx in range(active_questions):
            freq: dict[str, int] = {}
            total = 0
            # Gather unique correct keys for this question across all versions
            q_correct_keys = set()
            for ver in by_version.keys():
                keys = answer_key.get_version_keys(ver)
                q_correct_keys.update(keys.get(q_idx, set()))

            for g in grades:
                ans = g.answers[q_idx] if q_idx < len(g.answers) else ""
                key = ans if ans else "BLANK"
                freq[key] = freq.get(key, 0) + 1
                total += 1

            report.question_choices_overall.append(QuestionChoiceOverall(
                question_idx=q_idx,
                option_frequencies=freq,
                total_responses=total,
                correct_keys=sorted(list(q_correct_keys))
            ))

        # Item psychometrics (overall item difficulty, discrimination index, failure rate)
        high_low_n = max(1, int(len(grades) * 0.27))
        grades_with_idx = list(enumerate(grades))
        sorted_grades_idx = sorted(grades_with_idx, key=lambda x: x[1].score, reverse=True)
        high_group_idx = [x[0] for x in sorted_grades_idx[:high_low_n]]
        low_group_idx = [x[0] for x in sorted_grades_idx[-high_low_n:]]

        # Student responses in binary (1 correct, 0 incorrect)
        student_item_correct = []
        for g in grades:
            row = []
            keys = answer_key.get_version_keys(g.version)
            for q_idx in range(active_questions):
                q_correct_keys = keys.get(q_idx, set())
                ans = g.answers[q_idx] if q_idx < len(g.answers) else ""
                row.append(1 if ans in q_correct_keys else 0)
            student_item_correct.append(row)

        for q_idx in range(active_questions):
            q_display_keys = set()
            for ver in by_version.keys():
                keys = answer_key.get_version_keys(ver)
                q_display_keys.update(keys.get(q_idx, set()))

            item_scores = [student_item_correct[s_idx][q_idx] for s_idx in range(len(grades))]
            p_val = sum(item_scores) / len(grades) if grades else 0.0

            corr_high = sum(item_scores[s_idx] for s_idx in high_group_idx)
            corr_low = sum(item_scores[s_idx] for s_idx in low_group_idx)
            p_high = corr_high / high_low_n if high_low_n > 0 else 0.0
            p_low = corr_low / high_low_n if high_low_n > 0 else 0.0
            d_index = p_high - p_low

            # ── 1. Point-Biserial Correlation ──
            total_scores = [g.score for g in grades]
            c_scores = [total_scores[s_idx] for s_idx in range(len(grades)) if item_scores[s_idx] == 1]
            inc_scores = [total_scores[s_idx] for s_idx in range(len(grades)) if item_scores[s_idx] == 0]

            m1 = statistics.mean(c_scores) if c_scores else 0.0
            m0 = statistics.mean(inc_scores) if inc_scores else 0.0
            s_n = statistics.stdev(total_scores) if len(total_scores) > 1 else 1.0
            if s_n == 0:
                s_n = 1.0

            p_biserial = ((m1 - m0) / s_n) * math.sqrt(max(0, p_val * (1.0 - p_val)))

            # ── 2. Corrected Item-Total Correlation ──
            adj_scores = [total_scores[s_idx] - item_scores[s_idx] for s_idx in range(len(grades))]
            if len(grades) > 1 and statistics.stdev(item_scores) > 0 and statistics.stdev(adj_scores) > 0:
                mean_item = statistics.mean(item_scores)
                mean_adj = statistics.mean(adj_scores)
                cov = sum((item_scores[s_idx] - mean_item) * (adj_scores[s_idx] - mean_adj) for s_idx in range(len(grades))) / (len(grades) - 1)
                corr_corrected = cov / (statistics.stdev(item_scores) * statistics.stdev(adj_scores))
            else:
                corr_corrected = p_biserial

            # ── 3. Distractor Efficiency ──
            incorrect_choices = []
            for g_idx, g in enumerate(grades):
                if item_scores[g_idx] == 0:
                    ans = g.answers[q_idx] if q_idx < len(g.answers) else ""
                    if ans and ans != "BLANK":
                        incorrect_choices.append(ans)
            
            all_opts_q = set(report.active_options) - q_display_keys - {"", "BLANK"}
            func_distractors = 0
            for opt in all_opts_q:
                cnt = incorrect_choices.count(opt)
                if len(grades) > 0 and (cnt / len(grades)) >= 0.05:
                    func_distractors += 1
            d_eff = (func_distractors / len(all_opts_q)) * 100 if all_opts_q else 0.0

            # Quality classification
            if d_index >= 0.40:
                qc = "Excellent"
            elif d_index >= 0.30:
                qc = "Acceptable"
            elif d_index >= 0.10:
                qc = "Needs Review"
            else:
                qc = "Poor"

            report.item_psychometrics.append(ItemPsychometrics(
                question_idx=q_idx,
                correct_keys=sorted(list(q_display_keys)),
                p_value=round(p_val, 3),
                discrimination_index=round(d_index, 3),
                failure_rate=round(1.0 - p_val, 3),
                point_biserial=round(p_biserial, 3),
                corrected_item_total=round(corr_corrected, 3),
                distractor_efficiency=round(d_eff, 1),
                quality_class=qc
            ))

        # ── 4. KR-20 & Cronbach's Alpha ──
        k = active_questions
        total_scores = [g.score for g in grades]
        if k > 1 and len(total_scores) > 1:
            var_total = statistics.variance(total_scores)
            sum_item_vars = 0.0
            for q_idx in range(k):
                binary_item_scores = [student_item_correct[s_idx][q_idx] for s_idx in range(len(grades))]
                if len(binary_item_scores) > 1:
                    sum_item_vars += statistics.variance(binary_item_scores)

            if var_total > 0:
                kr20 = (k / (k - 1)) * (1.0 - sum_item_vars / var_total)
            else:
                kr20 = 0.0
        else:
            kr20 = 0.0

        kr20 = max(0.0, min(1.0, kr20))
        report.cronbach_alpha = round(kr20, 3)
        report.kr20 = round(kr20, 3)

        # ── 5. Split-Half Reliability ──
        odd_scores = []
        even_scores = []
        for g_idx, g in enumerate(grades):
            odd_sum = sum(student_item_correct[g_idx][q] for q in range(0, active_questions, 2))
            even_sum = sum(student_item_correct[g_idx][q] for q in range(1, active_questions, 2))
            odd_scores.append(odd_sum)
            even_scores.append(even_sum)

        if len(grades) > 1 and statistics.stdev(odd_scores) > 0 and statistics.stdev(even_scores) > 0:
            mean_odd = statistics.mean(odd_scores)
            mean_even = statistics.mean(even_scores)
            cov_half = sum((odd_scores[s] - mean_odd) * (even_scores[s] - mean_even) for s in range(len(grades))) / (len(grades) - 1)
            r_half = cov_half / (statistics.stdev(odd_scores) * statistics.stdev(even_scores))
            split_half = (2 * r_half) / (1 + r_half) if (1 + r_half) != 0 else 0.0
        else:
            split_half = kr20

        split_half = max(0.0, min(1.0, split_half))
        report.split_half_reliability = round(split_half, 3)

        # ── 6. Student Analytics ──
        for g in grades:
            below = sum(1 for s in all_scores if s < g.score)
            equal = sum(1 for s in all_scores if s == g.score)
            percentile = (below + 0.5 * equal) / len(all_scores) * 100 if all_scores else 0.0
            z = (g.score - report.overall_mean) / report.overall_stddev if report.overall_stddev > 0 else 0.0

            pct_score = (g.score / report.max_score) * 100 if report.max_score > 0 else 0.0
            if pct_score >= 85:
                mastery = "Mastery"
                band = "Advanced"
            elif pct_score >= 70:
                mastery = "Proficient"
                band = "Proficient"
            elif pct_score >= 50:
                mastery = "Developing"
                band = "Basic"
            else:
                mastery = "Remedial"
                band = "Below Basic"

            num_topics = math.ceil(active_questions / 5)
            weaknesses = []
            for t_idx in range(num_topics):
                q_start = t_idx * 5
                q_end = min(active_questions, q_start + 5)
                topic_correct = sum(student_item_correct[all_scores.index(g.score)][q] for q in range(q_start, q_end))
                topic_total = q_end - q_start
                if topic_total > 0 and (topic_correct / topic_total) < 0.6:
                    weaknesses.append(f"Domain {t_idx + 1}")

            report.student_analytics.append({
                "student_id": g.student_id,
                "version": g.version,
                "score": g.score,
                "percentile": round(percentile, 1),
                "z_score": round(z, 2),
                "mastery": mastery,
                "band": band,
                "weaknesses": ", ".join(weaknesses) if weaknesses else "None"
            })

        # ── 7. Topic-Based Analytics ──
        num_topics = math.ceil(active_questions / 5)
        for t_idx in range(num_topics):
            q_start = t_idx * 5
            q_end = min(active_questions, q_start + 5)
            topic_items = report.item_psychometrics[q_start:q_end]
            if topic_items:
                t_diff = statistics.mean([ip.p_value for ip in topic_items])
                t_disc = statistics.mean([ip.discrimination_index for ip in topic_items])
                report.topic_analyses.append({
                    "topic_id": f"Domain {t_idx + 1}",
                    "items": f"Q{q_start+1}-Q{q_end}",
                    "mean_difficulty": round(t_diff, 3),
                    "mean_discrimination": round(t_disc, 3),
                    "status": "Strong" if t_disc >= 0.3 else "Needs Review"
                })

        # Question choice analysis - per version
        for q_idx in range(active_questions):
            ver_pct: dict[str, dict[str, float]] = {}
            ver_correct_keys: dict[str, list[str]] = {}
            for ver, ver_grades in sorted(by_version.items()):
                keys = answer_key.get_version_keys(ver)
                ver_correct_keys[ver] = sorted(list(keys.get(q_idx, set())))
                freq: dict[str, int] = {}
                total = 0
                for g in ver_grades:
                    ans = g.answers[q_idx] if q_idx < len(g.answers) else ""
                    key = ans if ans else "BLANK"
                    freq[key] = freq.get(key, 0) + 1
                    total += 1
                pct_map = {}
                for opt_key, cnt in freq.items():
                    pct_map[opt_key] = round(cnt / total * 100, 0) if total > 0 else 0.0
                ver_pct[ver] = pct_map
            report.question_choices_by_version.append(QuestionChoiceByVersion(
                question_idx=q_idx,
                version_option_pct=ver_pct,
                version_correct_keys=ver_correct_keys
            ))

        # Fairness & ANOVA
        if len(report.version_stats) >= 2:
            means = [vs.mean for vs in report.version_stats]
            max_mean, min_mean = max(means), min(means)
            ms = report.max_score
            if ms > 0 and (max_mean - min_mean) > FAIRNESS_THRESHOLD * ms:
                report.fairness_verdict = "UNFAIR"
                report.fairness_explanation = (
                    f"Max version mean ({max_mean}) - Min version mean ({min_mean}) "
                    f"= {max_mean - min_mean:.2f}, exceeds {FAIRNESS_THRESHOLD*100:.0f}% of max score ({ms})."
                )
            else:
                report.fairness_verdict = "FAIR"
                report.fairness_explanation = "All version means are within acceptable range."

            # Version ranking by difficulty
            ranked = sorted(report.version_stats, key=lambda v: v.mean, reverse=True)
            for rank_idx, vs in enumerate(ranked):
                pct = vs.mean / report.max_score * 100 if report.max_score > 0 else 0
                if pct >= 75:
                    label = "Easy ✓"
                elif pct >= 55:
                    label = "Moderate"
                else:
                    label = "Hard ✗"
                report.version_ranking.append(VersionRankEntry(
                    version=vs.version, mean=vs.mean, difficulty_label=label
                ))

            # ANOVA
            groups = [vs.scores for vs in report.version_stats if vs.scores]
            versions = [vs.version for vs in report.version_stats if vs.scores]
            report.anova_f, report.anova_p = AnalysisEngine._anova_oneway(groups)
            report.kruskal_h, report.kruskal_p = AnalysisEngine._kruskal_wallis(groups)
            
            # Outlier versions
            report.grand_mean_versions = round(statistics.mean(means), 3)
            report.std_version_means = round(AnalysisEngine._safe_stddev(means), 3) if len(means) > 1 else 0.0
            for vs in report.version_stats:
                z = (vs.mean - report.grand_mean_versions) / report.std_version_means if report.std_version_means > 0 else 0.0
                label = ""
                if z > 1.2:
                    label = "← Significantly EASIER"
                elif z < -1.0:
                    label = "← Significantly HARDER"
                report.version_outliers.append(VersionOutlier(
                    version=vs.version, mean=vs.mean, z_score=round(z, 2), label=label
                ))

            if report.anova_p < 0.05:
                report.tukey_hsd_results = AnalysisEngine._tukey_hsd(groups, versions)

            # Score Equating (Mean Equating)
            target_mean = report.grand_mean_versions
            for vs in report.version_stats:
                adjustment = target_mean - vs.mean
                report.equated_scores[vs.version] = {
                    "adjustment": round(adjustment, 3),
                    "target_mean": round(target_mean, 3),
                    "original_mean": round(vs.mean, 3)
                }

        # At-Risk Student Identification
        pass_threshold = 0.6 * report.max_score
        for stu in report.student_analytics:
            if stu["score"] < pass_threshold:
                report.at_risk_students.append(stu)
        report.at_risk_students.sort(key=lambda x: x["score"])

        # Inter-Item Correlation Matrix (first 5 questions for simplicity)
        n_items = min(5, active_questions)
        matrix = [[1.0] * n_items for _ in range(n_items)]
        if len(grades) > 1 and n_items > 1:
            for i in range(n_items):
                scores_i = [student_item_correct[s][i] for s in range(len(grades))]
                std_i = statistics.stdev(scores_i) if len(scores_i) > 1 else 0
                for j in range(i + 1, n_items):
                    scores_j = [student_item_correct[s][j] for s in range(len(grades))]
                    std_j = statistics.stdev(scores_j) if len(scores_j) > 1 else 0
                    if std_i > 0 and std_j > 0:
                        mean_i = statistics.mean(scores_i)
                        mean_j = statistics.mean(scores_j)
                        cov = sum((scores_i[s] - mean_i) * (scores_j[s] - mean_j) for s in range(len(grades))) / (len(grades) - 1)
                        corr = cov / (std_i * std_j)
                        matrix[i][j] = round(corr, 3)
                        matrix[j][i] = round(corr, 3)
                    else:
                        matrix[i][j] = 0.0
                        matrix[j][i] = 0.0
        report.inter_item_correlation = matrix

        return report
