@echo off
start "MCP search" cmd /k "cd /d %~dp0scripts && python mcp_websearch.py"
cd /d D:\llama\llama-b12675-bin-win-cpu-x64
set LLAMA_CACHE=D:\llama\models
llama-server.exe -hf Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M --port 8080 -c 4096 --jinja --webui-mcp-proxy