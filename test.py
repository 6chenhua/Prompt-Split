import http.client
import json

conn = http.client.HTTPSConnection("api.rcouyi.com")
payload = json.dumps({
   "model": "gpt-5-mini",
   "messages": [
      {
         "role": "user",
         "content": "晚上好"
      }
   ],
   "max_tokens": 1688,
   "temperature": 0.5,
   "stream": False
})
headers = {
   'Authorization': 'Bearer sk-V0s4xmnT70wbwPPe160dBaCc96A74fB9Ae850fFc6dE6136b',
   'Content-Type': 'application/json'
}
conn.request("POST", "/v1/chat/completions", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))