import aiohttp
import asyncio

async def test_post():
    url = "http://localhost:5000/generate"  # try your suspected endpoint here
    payload = {"prompt": "Say hi", "max_tokens": 20}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            print(resp.status)
            print(await resp.text())

asyncio.run(test_post())
