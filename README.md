 Smart Demand Signals 
Inibsa · Interhack BCN 2026 
 
## Project Structure
 
- `src/`: Python scripts for data analysis and statistics.
- `data/`: Raw datasets in CSV and XLSX format.
- `docs/`: Documentation, hackathon briefings, and statistical reports.
- `plots/`: Generated visualizations and charts.
- `README.md`: Project overview and documentation.
 
1. Context and Motivation 
Inibsa is a locally-based pharmaceutical manufacturing company, committed to 
European standards and sustainability criteria such as efficient use of water and 
energy, among others. This challenge seeks to generate a business intelligence 
solution to promote the sale of its locally produced products, adhering to these 
European standards and sustainability criteria. It is presented at the Interhack BCN 
Hackathon within the BCN Clima framework. 
Inibsa operates with an approximate base of 7,000 dental clinics and has a sales 
history spanning more than five years at the client, product, and date level. This 
context allows tackling a high-value commercial challenge: transforming purchasing 
patterns into actionable predictive signals. 
The case presents two clearly different dynamics. On one hand, there are 
commoditised product categories with recurring purchases, tied to the clinic's 
habitual consumption — such as anaesthesia, needles, and disinfection products. In 
these families, not all clients show the same degree of engagement: some buy 
marginally or residually, others concentrate most of their demand with the company, 
and others alternate their purchases with competitors. The challenge is to detect 
these differences and, above all, identify the optimal moment of contact to capture 
demand that is not currently being materialised. 
On the other hand, there are technical products whose purchase depends more 
heavily on the type of clinical case, the professional's specialty, and competitor 
penetration within the account. In this area, the priority is not only to anticipate 
replenishment, but to detect early signals of deterioration in purchasing patterns or 
risk of abandonment. 
2. Challenge Objective 
Design an analytical solution capable of identifying, on a daily basis, signals 
indicating the need for commercial intervention at the level of client, product family, 
and timing — differentiating between two main use cases: commodity products and 
technical products. 
The company is looking for a solution capable of converting transactional and 
commercial data into interpretable and actionable alerts, directed to the appropriate 
channel in each case: sales representative, telesales, or marketing automation. The 
solution should initially be designed as standalone, with the possibility of future 
integration into a CRM or other platforms, without depending on a specific 
technology. 
In this way, the solution contributes to promoting the sale of Inibsa's locally produced 
products, following European standards and sustainability criteria such as efficient 
use of water and energy, while better anticipation of demand implies a more efficient 
supply chain. 
3. Technical Challenge / Functional Requirements 
The solution must treat commodity products with recurring purchases and technical 
products with more variable patterns differently. For commodities, it must estimate 
each client's expected purchasing behaviour relative to their consumption potential, 
distinguishing between clients with zero or marginal purchases, loyal clients, and 
promiscuous clients who split their demand with competitors. For technical products, 
it must identify signals of risk of loss or abandonment, detecting drops in frequency, 
drops in volume, total disappearance of purchases, or anomalous activity relative to 
the client's historical pattern. 
The system must recalculate signals and alerts on a daily basis, on a stable and 
maintainable update foundation. Each alert must include a contact recommendation, 
reason, and affected product family, and must offer the ability to reconstruct why it 
was generated and which variables or rules were involved in its activation. 
The solution should not be limited to generating alerts, but must help to order and 
operationalise them, incorporating expected economic impact, conversion 
probability, and time urgency. The resulting action may be directed to a sales 
representative, telesales, or marketing platform (e.g. HubSpot), depending on the 
commercial assignment of the client. The proposal must be agnostic with respect to 
specific CRMs and must contemplate what happens after the alert: who manages it, 
within what timeframe, and how its result is recorded. 
4. Available Resources and Data 
Inibsa has information at the client and product level with daily granularity, purchase 
channel, representative or telesales activity, client data (purchasing potential, 
location, client type), and some indirect and qualitative indications about competitors. 
The solution must explicitly address aspects of data quality, consistency, and 
traceability — managing clients with incomplete histories, normalisation of product 
families, product changes or substitutions, and clients with irregular or seasonal 
purchases. It must also handle anomalies that could distort the signal, such as 
extraordinary orders, promotions, stock breaks, or changes in commercial policy. 
Part of the CRM commercial activity is in free-text format, so its use should be 
considered optional or exploratory. Data reliability is higher in Spain than in Portugal, 
which is why the initial development will focus on Spain. 
5. Expected Deliverables 
Each team must develop a proposal capable of translating the available data into a 
useful tool for commercial action. Ideally, the solution will offer: prediction of 
purchase need for commodities, early detection of churn risk for technical products, 
clear identification of capture windows against competitors, interpretable and 
actionable alerts, operational prioritisation, a proposal for daily operation, and an 
architecture to operate standalone and later evolve towards CRM integration. 
The solution must also contemplate the capacity to learn from its own use, by 
recording the generated alert, the commercial action taken, and the result obtained, 
so as to improve the model, detect false positives, and adjust rules or parameters 
over time. 
6. Evaluation Criteria 
Proposals will be especially valued on: the ability to translate a complex business 
problem into a useful analytical solution; intelligent differentiation between 
commodity and technical products; quality of the predictive logic; interpretability and 
traceability of alerts; prioritisation capability and fit within the commercial process; 
real applicability in a commercial environment; and scalability and viability of future 
evolution.