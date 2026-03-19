import psycopg

conn = psycopg.connect('postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation')
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM claude.vault_embeddings')
total = cur.fetchone()[0]
print(f'Total embeddings: {total}')

if total > 0:
    cur.execute('SELECT doc_path, COUNT(*) as cnt FROM claude.vault_embeddings GROUP BY doc_path ORDER BY doc_path')
    rows = cur.fetchall()
    print(f'\nDocuments with embeddings: {len(rows)}')
    for row in rows:
        print(f'  {row[0]}: {row[1]} chunks')

conn.close()
