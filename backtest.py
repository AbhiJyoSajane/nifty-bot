from kiteconnect import KiteConnect

API_KEY = btj1h6qbwop4gah2
API_SECRET = 3r0r7i5b13ll8um9r6wtwrtwv51rv4ev
REQUEST_TOKEN = hmVK06HJzG36Da5tpDT6j6OigxDVNgfs

kite = KiteConnect(api_key=API_KEY)

data = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)

print("ACCESS TOKEN:", data["access_token"])
