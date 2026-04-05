from kiteconnect import KiteConnect

kite = KiteConnect(api_key="btj1h6qbwop4gah2")

data = kite.generate_session(
    "pQ7LcW4G7PHA70VwvSvWQQW8mzQL7Ttz",
    api_secret="3r0r7i5b13ll8um9r6wtwrtwv51rv4ev"
)

print(data["access_token"])
