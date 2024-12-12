from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class Memory:
    def __init__(self, summary, embedding):
        self.summary = summary
        self.embedding = embedding


class MemoryService:
    def __init__(self):
        self.experiences = []
        self.memory_model = SentenceTransformer('./Models/all-MiniLM-L6-v2')

    def generate_embedding(self, text):
        return self.memory_model.encode(text)

    def get_similar_memories(self, embedding, threshold=0.5):
        relevant_memories = []
        for experience in self.experiences:
            similarity = cosine_similarity([embedding], [experience.embedding])[0][0]
            if similarity > threshold:
                relevant_memories.append(experience)
        return relevant_memories

    def add_memory(self, summary):
        embedding = self.generate_embedding(summary)
        self.experiences.append(Memory(summary, embedding))

    def get_all_memories(self):
        """
        获取所有存储的记忆总结，返回一个列表，其中每个元素是记忆的summary。
        """
        return [experience.summary for experience in self.experiences]

    def reset(self):
        self.experiences = []
