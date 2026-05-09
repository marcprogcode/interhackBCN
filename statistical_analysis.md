# Statistical Analysis Report

This report summarizes the statistical findings based on the visual exploratory data analysis (EDA) previously conducted on the client dataset.

## 1. Lifetime Purchasing Value (LTV) Distribution
The distribution of total lifetime value per client (N=8,095) is highly right-skewed, adhering closely to the Pareto principle.

*   **Mean LTV:** €13,518.51
*   **Median LTV:** €5,528.85
*   **Standard Deviation:** €26,506.67
*   **Skewness:** 8.31 (Highly skewed to the right)
*   **Kurtosis:** 139.22 (Extreme outlier presence/heavy tails)

**Percentile Breakdown:**
*   **Bottom 25%:** Under €1,895.92
*   **Top 25%:** Over €14,066.93
*   **Top 10%:** Over €31,842.23

**Interpretation:** The vast difference between the mean and the median, along with extreme skewness and kurtosis, proves mathematically what the histogram showed: a small number of very high-value clients generate a disproportionately large amount of revenue.

---

## 2. Client Tenure (Active Lifespan) Distribution
Tenure is defined as the days between a client's first and most recent purchase. 

*   **Mean Tenure:** 1,023.77 days (~2.8 years)
*   **Median Tenure:** 1,238.00 days (~3.4 years)
*   **Standard Deviation:** 668.00 days

**Percentile Breakdown:**
*   **25th Percentile:** 346 days (Clients who stopped buying or are new within ~1 year)
*   **75th Percentile:** 1,662 days (~4.5 years)

**Interpretation:** The median being higher than the mean indicates a left-skew in survival terms—a large core of loyal clients stick around for 3.4+ years, while a subset drops off early (bringing the mean down).

---

## 3. Relationship: Tenure vs. Lifetime Value
To quantify the scatter plot showing Tenure vs LTV, we ran correlation tests.

*   **Pearson Correlation (Linear):** 0.3914 (p-value: < 0.0001)
*   **Spearman Correlation (Rank-based):** 0.7906 (p-value: < 0.0001)

**Interpretation:** The Pearson correlation is moderate (0.39) due to extreme LTV outliers breaking the linear scale. However, the **Spearman correlation is very strong (0.79)**. This means that *rank order* is highly consistent: as clients stay longer, their relative LTV rank reliably goes up. Loyalty is a massive driver of accumulated value.

---

## 4. Comparative Analysis: Bottom 25% vs Top 25% Spenders
We filtered for clients with > 2 years of tenure and compared a random sample (N=100) of the Top 25% vs Bottom 25% based on their *Average Purchase Price*.

*   **Bottom 25% Sample:** Mean Tx Value = €271.09 | Variance = 42,182.32
*   **Top 25% Sample:** Mean Tx Value = €1,245.83 | Variance = 1,610,325.63

**Statistical Tests on Individual Transactions:**
*   **Mann-Whitney U Test:** p-value ≈ 0.0000 
    * *Conclusion:* The median transaction values of the two groups are definitively drawn from different distributions. 
*   **Levene's Test (Equality of Variances):** p-value < 0.0001 
    * *Conclusion:* The top spenders have statistically significantly higher variance. They don't just spend more on average; their transaction sizes are vastly more erratic.

---

## 5. Spending Habits: Time Series Trend Comparison
To determine if the spending habits "follow each other" (from the dual-axis line chart), we correlated their monthly aggregate spending over time.

*   **Pearson Correlation (Monthly Aggregates):** 0.6035 (p-value < 0.0001)

**Interpretation:** A correlation of ~0.60 indicates a **moderate-to-strong positive relationship** in their spending rhythms over time. Both groups tend to peak and dip during the same months, confirming that broader business seasonality or market forces impact both low and high spenders similarly, even if the scale of their spending is entirely different.
