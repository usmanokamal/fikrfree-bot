# 🚀 FikrFree Assistant API - Quick Start

## Test the API in 30 Seconds

```bash
# 1. Health check
curl https://your-domain.com/api/v1/health

# 2. Quick test
curl -X POST https://your-domain.com/api/v1/sessions/start

# 3. Chat test
SESSION_ID="your-session-id-here"
curl -X POST https://your-domain.com/api/v1/sessions/$SESSION_ID/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are BIMA insurance plans?"}'
```

## Python (Easiest)

```python
from fikrfree_client_sdk import FikrFreeClient

with FikrFreeClient("https://your-domain.com/api/v1") as client:
    response = client.chat("What insurance do you offer?")
    print(response.response)
```

## JavaScript

```javascript
const client = new FikrFreeClient('https://your-domain.com/api/v1');
const response = await client.chat('Tell me about BIMA');
console.log(response.response);
```

## 📖 Next Steps

1. **Start Here**: Read `README.md`
2. **Full Docs**: Check `API_DOCUMENTATION.md`  
3. **Examples**: See `CLIENT_EXAMPLES.md`
4. **Live Testing**: Visit https://your-domain.com/docs

## Key Features

✅ **Bilingual** - English & Roman Urdu  
✅ **Context-Aware** - Remembers conversation  
✅ **Healthcare Expert** - Pakistani insurance specialist  
✅ **Real-time** - Streaming responses available  
✅ **Production Ready** - Secure & scalable