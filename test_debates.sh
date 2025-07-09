#\!/bin/bash

# Array of complex questions to test
declare -a questions=(
  "Should we add unit tests for the evolution tracker module?"
  "Should we implement a plugin architecture for extensibility?"
  "Should we add real-time monitoring and observability features?"
  "Should we implement a rollback mechanism for failed deployments?"
  "Should we add multi-language support for international users?"
)

# Array to store PR numbers
declare -a pr_numbers=()

echo "Starting complex decision debates..."

for i in "${\!questions[@]}"; do
  echo -e "\n=== Debate $((i+1)): ${questions[$i]} ==="
  
  # Run the debate
  response=$(curl -s -X POST http://localhost:8000/decide \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"${questions[$i]}\", \"context\": \"Testing PR creation for complex decisions\"}")
  
  # Extract timestamp
  timestamp=$(echo "$response" | jq -r '.time')
  echo "Debate completed at: $timestamp"
  
  # Wait a bit for PR creation
  sleep 5
  
  # Get the latest PR
  latest_pr=$(gh pr list --state all --limit 1 --json number,title,url | jq -r '.[0]')
  pr_number=$(echo "$latest_pr" | jq -r '.number')
  pr_title=$(echo "$latest_pr" | jq -r '.title')
  pr_url=$(echo "$latest_pr" | jq -r '.url')
  
  echo "Created PR #$pr_number: $pr_title"
  echo "URL: $pr_url"
  
  pr_numbers+=("$pr_number")
  
  # Wait between debates to avoid rate limiting
  sleep 10
done

echo -e "\n=== Summary of Created PRs ==="
for pr in "${pr_numbers[@]}"; do
  gh pr view "$pr" --json number,title,url,state | jq -r '"PR #\(.number): \(.title)\nURL: \(.url)\nState: \(.state)\n"'
done
