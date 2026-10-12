-- Q1 row counts
SELECT 'companies' t, COUNT(*) n FROM companies UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices UNION ALL SELECT 'financial_ratios', COUNT(*) FROM financial_ratios;
-- Q2 companies per broad sector
SELECT broad_sector, COUNT(*) companies FROM sectors GROUP BY broad_sector ORDER BY companies DESC;
-- Q3 P&L year coverage per company (shortest first)
SELECT company_id, COUNT(*) yrs, MIN(year) first_yr, MAX(year) last_yr FROM profitandloss GROUP BY company_id ORDER BY yrs LIMIT 10;
-- Q4 companies with fewer than 10 P&L years
SELECT COUNT(*) companies_lt_10yrs FROM (SELECT company_id FROM profitandloss GROUP BY company_id HAVING COUNT(*) < 10);
-- Q5 nulls in key P&L columns
SELECT SUM(sales IS NULL) null_sales, SUM(net_profit IS NULL) null_net_profit, SUM(eps IS NULL) null_eps, SUM(interest IS NULL) null_interest FROM profitandloss;
-- Q6 balance sheet years-per-company distribution
SELECT yrs, COUNT(*) companies FROM (SELECT company_id, COUNT(*) yrs FROM balancesheet GROUP BY company_id) GROUP BY yrs ORDER BY yrs;
-- Q7 duplicate (company_id, year) in P&L (expect 0 rows)
SELECT company_id, year, COUNT(*) c FROM profitandloss GROUP BY company_id, year HAVING c > 1;
-- Q8 companies with no balance sheet rows
SELECT id FROM companies WHERE id NOT IN (SELECT company_id FROM balancesheet);
-- Q9 top 10 companies by latest-year sales
SELECT company_id, year, sales FROM profitandloss WHERE year = '2024-03-31' ORDER BY sales DESC LIMIT 10;
-- Q10 companies with fewer than 10 annual report links
SELECT c.id, COUNT(d.id) reports FROM companies c LEFT JOIN documents d ON d.company_id = c.id GROUP BY c.id HAVING reports < 10 ORDER BY reports LIMIT 15;