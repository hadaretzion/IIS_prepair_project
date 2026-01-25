$base = 'http://localhost:8000'

# Ensure user
$userResponse = Invoke-RestMethod -Method POST -Uri "$base/api/users/ensure" -Body (@{ user_id = '' } | ConvertTo-Json) -ContentType 'application/json'
$userId = $userResponse.user_id

# Simple CV/JD
$cvText = 'John Doe Backend Engineer with 5 years experience in Python, FastAPI, SQL, Docker. Built APIs, deployed on AWS, used PostgreSQL and Redis.'
$jdText = 'Hiring a backend engineer to build REST APIs with FastAPI, SQL databases, Docker, AWS. Looking for Python skills and system design.'

$cv = Invoke-RestMethod -Method POST -Uri "$base/api/cv/ingest" -Body (@{ user_id=$userId; cv_text=$cvText } | ConvertTo-Json) -ContentType 'application/json'
$jd = Invoke-RestMethod -Method POST -Uri "$base/api/jd/ingest" -Body (@{ user_id=$userId; jd_text=$jdText } | ConvertTo-Json) -ContentType 'application/json'

$start = Invoke-RestMethod -Method POST -Uri "$base/api/interview/start" -Body (@{ user_id=$userId; job_spec_id=$jd.job_spec_id; cv_version_id=$cv.cv_version_id; mode='direct'; settings=@{ num_open=1; num_code=1; duration_minutes=5 } } | ConvertTo-Json) -ContentType 'application/json'
$sessionId = $start.session_id
$firstQ = $start.first_question.text

$answer1 = 'I designed and built FastAPI services on AWS using Docker. For performance I used async endpoints and caching with Redis. I wrote integration tests and CI/CD pipelines.'
$next = Invoke-RestMethod -Method POST -Uri "$base/api/interview/next" -Body (@{ session_id=$sessionId; user_transcript=$answer1; user_code=$null; is_followup=$false } | ConvertTo-Json) -ContentType 'application/json'
$secondQ = $next.next_question.text

$answer2 = 'For SQL tuning I use proper indexes, EXPLAIN plans, and connection pooling. I also monitor slow queries and add caching where appropriate.'
Invoke-RestMethod -Method POST -Uri "$base/api/interview/next" -Body (@{ session_id=$sessionId; user_transcript=$answer2; user_code=$null; is_followup=$false } | ConvertTo-Json) -ContentType 'application/json' | Out-Null

Invoke-RestMethod -Method POST -Uri "$base/api/interview/end" -Body (@{ session_id=$sessionId } | ConvertTo-Json) -ContentType 'application/json' | Out-Null

Write-Output "Mock interview complete. SessionId=$sessionId"
Write-Output "First question: $firstQ"
Write-Output "Second question: $secondQ"
