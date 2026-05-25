# save as test_rag.py in GenEV/ and run: python test_rag.py
import sys
sys.path.insert(0, ".")

from rag.embeddings import get_or_build_index, retrieve

print("Building index...")
collection = get_or_build_index()
print(f"Index ready: {collection.count()} chunks")

results = retrieve("What is the range of Tata Nexon EV?", top_k=3)
for r in results:
    print(f"\nSource: {r['source']} | Score: {r['score']}")
    print(r['text'][:200])