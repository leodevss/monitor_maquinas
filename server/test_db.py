import asyncpg
import asyncio
import ssl

async def main():
    DATABASE_URL = "postgres://postgres:teste234534524@db.vtxzykyluwqihqmhkurm.supabase.co:5432/postgres"

    # SSL sem verificação — APENAS PARA TESTE
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    print("Conectando...")
    conn = await asyncpg.connect(DATABASE_URL, ssl=ssl_ctx)
    print("Conectado!")
    result = await conn.fetchval("SELECT NOW();")
    print("SELECT NOW() ->", result)
    await conn.close()

asyncio.run(main())
