from app.service.vector_knowledge_service import VectorKnowledgeService


def main():
    service = VectorKnowledgeService()
    result = service.rebuild_index()
    print(result)


if __name__ == "__main__":
    main()
