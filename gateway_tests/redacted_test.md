```
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "My email is test@example.com and my phone is 555-123-4567"}
    ]
  }' | python -m json.tool
```  