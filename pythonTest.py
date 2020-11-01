import time, asyncio

async def task1():
    for i in range(2):
        print("Task1 : {} second(s)".format(i))
        await asyncio.sleep(1)

async def task2():
    for i in range(2):
        print("Task2: {} second(s)".format(i))
        await asyncio.sleep(1)

async def main():
    await task1()
    await task2()

asyncio.run(main())

print("The End")


