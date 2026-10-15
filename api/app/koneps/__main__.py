"""로컬 확인용: 최신 공고를 조회해 출력한다.

    cd api
    python -m app.koneps            # 용역 10건
    python -m app.koneps 공사 5
"""

import asyncio
import sys

from app.config import get_settings
from app.koneps.client import KonepsClient


async def main() -> None:
    category = sys.argv[1] if len(sys.argv) > 1 else "용역"
    num_rows = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    settings = get_settings()
    client = KonepsClient(settings.data_go_kr_service_key, settings.koneps_base_url)
    bids = await client.fetch_latest(category, num_rows)
    print(f"[{category}] 최신 {len(bids)}건")
    for bid in bids:
        price = f"{bid.presmpt_prce:,}원" if bid.presmpt_prce else "-"
        print(f"- {bid.bid_ntce_dt} | {bid.bid_ntce_no}-{bid.bid_ntce_ord} | {bid.bid_ntce_nm} | {bid.ntce_instt_nm} | {price}")


if __name__ == "__main__":
    asyncio.run(main())
