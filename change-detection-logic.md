# Smart Change Detection for Microservices

## Dependency Mapping

Each microservice depends on:
1. **Base Layer** (if using base-layer)
2. **Core Layer** (if using core-layer) 
3. **Database Layer** (if using database-layer)
4. **ML Layer** (if using ml-layer)
5. **Specific Layer** (pdf-processor-layer, easyocr-layer, etc.)
6. **Handler Python file**
7. **Requirements file** (if any)

## Change Detection Logic

A microservice needs to be rebuilt if:
- Its handler Python file changed
- Its Dockerfile changed
- Its requirements file changed
- Any of its dependency layers changed
- Any shared files it depends on changed

## Implementation Strategy

1. **Detect changed files** using `git diff`
2. **Map changes to affected services** using dependency graph
3. **Skip unchanged services** in GitHub Actions matrix
4. **Build only affected layers and services**
