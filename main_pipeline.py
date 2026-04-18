import asyncio
import sys
import argparse
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

from test_parser import run_all_scrapers
from analyze_jobs import start_analysis

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", default="Python")
    parser.add_argument("--exp", default="no")
    parser.add_argument("--skills", default="")
    parser.add_argument("--sources", default="djinni,dou,linkedin")
    args = parser.parse_args()

    selected_sources = args.sources.split(",")

    print(f"🤖 === STARTING PIPELINE: {args.keyword} === 🤖")
    print(f"Sources: {selected_sources}")

    await run_all_scrapers(
        keyword=args.keyword,
        exp=args.exp,
        selected_sources=selected_sources
    )

    await start_analysis(user_skills=args.skills)

    print("\n✅ PIPELINE FINISHED.")

if __name__ == "__main__":
    asyncio.run(main())