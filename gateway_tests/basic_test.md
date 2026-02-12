```
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello! What is AI governance?"}
    ]
  }' | python3 -m json.tool
```  