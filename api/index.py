import traceback
import sys

try:
    from mangum import Mangum
    from backend.main import app
    handler = Mangum(app, lifespan="off")
except Exception as e:
    tb = traceback.format_exc()
    print(f"IMPORT ERROR: {e}\n{tb}", file=sys.stderr)

    async def handler(event, context):
        return {
            "statusCode": 500,
            "headers": {"content-type": "application/json"},
            "body": f'{{"error": "{str(e)}", "traceback": "{tb[:500]}"}}'
        }
