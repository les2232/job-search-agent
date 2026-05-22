# Job Search Agent

A private, local-first Python project for evaluating job postings, scoring role
fit, and tracking application opportunities with sample data.

This first milestone reads one fake job description, parses basic fields,
scores it with keyword rules, prints a recommendation, and saves a local CSV
result.

## Run

```powershell
python .\src\main.py
```

## Safety Notes

- No real resumes, emails, job history, credentials, or API keys are included.
- `config.yaml` is ignored; use `config.example.yaml` for safe examples only.
- `data/jobs.csv` is generated locally and ignored by Git.
- The project does not scrape login-protected sites or automate applications.
