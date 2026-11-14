# PROJECT ATLAS — MILESTONE 13Q
# ACTIVE LEARNING & EXPECTED INFORMATION GAIN (EIG)
## Mathematical Formulations, Bayesian Posteriors & Non-Probabilistic Deterministic Bounds

**Milestone:** 13Q — Atlas Autonomous Science Discovery Engine  
**Module:** `src/marswalk/core/science_observation_value.py`  
**Status:** `QUALIFIED`

---

## 1. Information-Theoretic Foundations

At the heart of autonomous science discovery lies **Active Learning**: selecting the next robotic observation that maximizes expected reduction in epistemic uncertainty.

### 1.1. Shannon Entropy of the Hypothesis Space
For a finite set of $N$ competing scientific hypotheses $\mathcal{H} = \{H_1, H_2, \dots, H_N\}$ with probability distribution $P(H_i)$, the Shannon entropy is defined in bits as:

$$H(\mathcal{H}) = -\sum_{i=1}^{N} P(H_i) \log_2 P(H_i)$$

- If the system is completely uncertain among two equal explanations ($P_1 = P_2 = 0.5$), $H = 1.0\text{ bit}$.
- If three explanations are equally probable ($P_i = 1/3$), $H = \log_2(3) \approx 1.585\text{ bits}$.
- When a hypothesis is conclusively proven ($P_1 = 1.0, P_{i>1} = 0.0$), $H = 0.0\text{ bits}$.

### 1.2. Expected Information Gain (EIG)
Given current evidence $D$, a proposed observation action $a$ yields possible outcomes $y \in \mathcal{Y}$. The Expected Information Gain is the difference between prior entropy and the expected posterior entropy across all anticipated measurement outcomes:

$$EIG(a) = H(\mathcal{H} \mid D) - \mathbb{E}_{y \sim p(y \mid a, D)} \left[ H(\mathcal{H} \mid D, y, a) \right]$$

Expanding the expectation over marginal outcome probabilities $p(y_j) = \sum_i P(y_j \mid H_i) P(H_i)$:

$$EIG(a) = H(\mathcal{H} \mid D) - \sum_{j} p(y_j) \left[ -\sum_{i} P(H_i \mid y_j) \log_2 P(H_i \mid y_j) \right]$$

where the posterior is updated via Bayes' rule:

$$P(H_i \mid y_j) = \frac{P(y_j \mid H_i) P(H_i)}{p(y_j)}$$

---

## 2. Mathematical Integrity Invariants

1. **Uninformative Tests Yield Zero EIG:** If an instrument produces identical outcome likelihoods regardless of the underlying truth ($P(y \mid H_1) = P(y \mid H_2) = 0.5$), the engine mathematically proves $EIG = 0.0\text{ bits}$. No false scientific gain is attributed to redundant or uninformative sensing.
2. **Deterministic Fallbacks:** Where calibrated probability distributions are unjustified, the engine strictly suppresses probabilistic EIG and computes deterministic metrics:
   - **Interval-Width Reduction:** $\Delta W(a) = W_{\text{curr}} - \mathbb{E}[W_{\text{post}}]$
   - **Spatial Coverage Expansion:** $\Delta C(a)$
   - **Discriminating Divergence:** Jensen-Shannon divergence between likelihood profiles.
