SELECT
  CAST(EmployeeNumber AS INTEGER) AS employee_number,
  TRIM(LOWER(Department)) AS department,
  TRIM(LOWER(JobRole)) AS job_role,
  CAST(JobLevel AS INTEGER) AS job_level,
  CASE
    WHEN TRIM(LOWER(CAST(OverTime AS VARCHAR))) IN ('yes', 'true') THEN TRUE
    ELSE FALSE
  END AS over_time,
  CAST(MonthlyIncome AS DECIMAL(12, 2)) AS monthly_income,
  CAST(PercentSalaryHike AS INTEGER) AS percent_salary_hike,
  CAST(YearsAtCompany AS INTEGER) AS years_at_company,
  CAST(YearsSinceLastPromotion AS INTEGER) AS years_since_last_promotion,
  CAST(TotalWorkingYears AS INTEGER) AS total_working_years,
  CAST(JobSatisfaction AS INTEGER) AS job_satisfaction,
  CAST(EnvironmentSatisfaction AS INTEGER) AS environment_satisfaction,
  CAST(RelationshipSatisfaction AS INTEGER) AS relationship_satisfaction,
  CAST(WorkLifeBalance AS INTEGER) AS work_life_balance,
  CASE
    WHEN TRIM(LOWER(CAST(Attrition AS VARCHAR))) IN ('yes', 'true') THEN TRUE
    ELSE FALSE
  END AS attrition,
  CAST({{source_file}} AS VARCHAR) AS source_file,
  CAST({{run_id}} AS VARCHAR) AS run_id,
  CAST({{processed_at_utc}} AS TIMESTAMP) AS processed_at_utc
FROM bronze_hr_attrition
