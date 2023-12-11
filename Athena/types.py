# https://github.com/gatariee/Winton/blob/main/client/Winton/types.py

from dataclasses import dataclass

@dataclass
class Agent:
    IP: str
    ExtIP: str
    Hostname: str
    Sleep: str
    Jitter: str
    OS: str
    UID: str
    PID: str

    def winton(self) -> dict:
        return self.__dict__


@dataclass
class File:
    Filename: str
    Size: int
    IsDir: bool
    ModTime: str

    def winton(self) -> dict:
        return self.__dict__


@dataclass
class CommandData:
    CommandID: str
    Command: str

    def winton(self) -> dict:
        return self.__dict__


@dataclass
class Command:
    name: str
    description: str
    usage: str

    def __str__(self):
        return f"{self.name}\t\t{self.description}\nUsage: {self.usage}"


@dataclass
class Result:
    CommandID: str
    Result: str

    def winton(self) -> dict:
        return self.__dict__


@dataclass
class ResultList:
    results: list[Result]

    def winton(self) -> dict:
        return self.__dict__