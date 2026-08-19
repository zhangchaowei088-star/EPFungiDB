# Fungi Database Django Backend

This backend imports the prepared TSV files under `tables/` into Django models and exposes read-only REST APIs for a killing-fungi database.

## Local Setup

```bash
python3 -m pip install -r requirements.txt
python3 manage.py migrate
```

Quick import for development, excluding million-row protein-level tables:

```bash
python3 manage.py import_ready_tables --truncate --skip-large
```

Full import:

```bash
python3 manage.py import_ready_tables --truncate --batch-size 5000
```

The full import includes `proteins.tsv`, `protein_general_annotation_summary.tsv`, `protein_pathogenicity_summary.tsv`, `kegg_pathway_members.tsv`, and `protein_pathogenicity_features.tsv`. These tables contain millions of rows, so run the command as a background job on the server after checking load.

## API Entrypoints

- `GET /`: dashboard homepage consuming the REST APIs below.
- `GET /api/summary/`: database-level counts for the homepage.
- `GET /api/samples/`: sample list with filters, search, ordering, and pagination.
- `GET /api/samples/{sample_id}/`: sample detail with genome, BUSCO, antiSMASH, SignalP, functional, and pathogenicity summaries.
- `GET /api/samples/{sample_id}/proteins/`: proteins for one sample.
- `GET /api/samples/{sample_id}/kegg-pathways/`: KEGG pathway counts for one sample.
- `GET /api/proteins/`: protein search.
- `GET /api/proteins/{protein_uid}/`: protein detail.
- `GET /api/kegg-pathway-members/?sample_id=A_G78&kegg_pathway_id=ko00511`: pathway genes/proteins for one sample.
- `GET /api/pathogenicity-features/`: long-table pathogenicity-associated features.
- `GET /api/annotation-sources/`: source definitions and interpretation notes.

Pagination supports `page` and `page_size`; `page_size` is capped at 500.

## Notes

- `sample_id` is the primary business key for samples.
- `protein_uid` is the primary business key for proteins.
- Pathogenicity-associated fields are candidate features, not experimentally validated pathogenic genes.
- SQLite is fine for development. For production and full protein-level imports, use PostgreSQL or another server-grade relational database.
