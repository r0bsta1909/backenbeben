"""Load the project-local MCP add-on without changing global Blender preferences."""
import importlib.util
import os
from pathlib import Path
import bpy

root = Path(__file__).resolve().parents[1]
os.environ['DISABLE_TELEMETRY'] = 'true'
spec = importlib.util.spec_from_file_location('slap_blender_mcp', root / 'tools/blender-mcp/addon.py')
addon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(addon)
addon.register()
bpy.context.scene.blendermcp_auto_start_server = False
server = addon.BlenderMCPServer(host='127.0.0.1', port=9876)
bpy.types.blendermcp_server = server
server.start()
bpy.context.scene.blendermcp_server_running = True
print('SLAP: Blender MCP bridge ready on 127.0.0.1:9876', flush=True)
