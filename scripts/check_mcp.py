"""Read-only end-to-end MCP smoke check; Blender must already be running."""
import asyncio
import json
import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    env = dict(os.environ, BLENDER_HOST='127.0.0.1', BLENDER_PORT='9876', DISABLE_TELEMETRY='true')
    params = StdioServerParameters(command=sys.executable, args=['-m', 'blender_mcp.server'], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            result = await session.call_tool('get_scene_info', {})
            report = {'tools': [t.name for t in listing.tools], 'scene': result.model_dump(mode='json')}
            Path('tools/mcp-smoke.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(report, indent=2))
            if result.isError:
                raise RuntimeError('MCP scene query failed')

asyncio.run(main())
