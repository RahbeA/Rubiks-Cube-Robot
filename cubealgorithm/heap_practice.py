import heapq

frontier = []
counter = 0

heapq.heappush(frontier, (3, counter, "state_b"))
counter+=1
heapq.heappush(frontier, (3, counter, "state_a"))
counter+=1
heapq.heappush(frontier, (1, counter, "state_c"))
counter+=1





for i in range(3):
    print(heapq.heappop(frontier))