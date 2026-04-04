SELECT
  employee_number AS employee_id,
  CAST({{ingestion_date}} AS DATE) AS ingestion_date,
  CAST({{year}} AS INTEGER) AS year,
  CAST({{month}} AS INTEGER) AS month,
  CAST({{day}} AS INTEGER) AS day,
  department,
  job_role,
  job_level,
  attrition,
  monthly_income,
  percent_salary_hike,
  years_at_company,
  years_since_last_promotion,
  total_working_years,
  over_time,
  job_satisfaction AS job_satisfaction_score,
  environment_satisfaction AS environment_satisfaction_score,
  relationship_satisfaction AS relationship_satisfaction_score,
  work_life_balance AS work_life_balance_score,
  CASE job_satisfaction
    WHEN 1 THEN 'low'
    WHEN 2 THEN 'medium'
    WHEN 3 THEN 'high'
    WHEN 4 THEN 'very_high'
  END AS job_satisfaction_label,
  CASE environment_satisfaction
    WHEN 1 THEN 'low'
    WHEN 2 THEN 'medium'
    WHEN 3 THEN 'high'
    WHEN 4 THEN 'very_high'
  END AS environment_satisfaction_label,
  CASE relationship_satisfaction
    WHEN 1 THEN 'low'
    WHEN 2 THEN 'medium'
    WHEN 3 THEN 'high'
    WHEN 4 THEN 'very_high'
  END AS relationship_satisfaction_label,
  CASE work_life_balance
    WHEN 1 THEN 'low'
    WHEN 2 THEN 'medium'
    WHEN 3 THEN 'high'
    WHEN 4 THEN 'very_high'
  END AS work_life_balance_label,
  source_file,
  CAST({{run_id}} AS STRING) AS run_id,
  CAST({{processed_at_utc}} AS TIMESTAMP) AS processed_at_utc
FROM silver_hr_employees
