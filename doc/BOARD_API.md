# Board System API Documentation

## Overview

The Board System provides a complete RESTful API for managing discussion forums with posts, comments, and reactions (likes/bookmarks). The system supports full-text search, nested comments (2 levels), and real-time engagement metrics.

**Base URL:** `/api/v1/board`

**Required Headers:**
- `X-API-Key`: API key for authentication
- `X-Platform`: Platform identifier (`web`, `mobile`, `desktop`, `device`)
- `Authorization`: Bearer token (for authenticated endpoints)

---

## Categories

### List Categories
```
GET /categories
```

**Authentication:** Optional
**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "name": "General",
    "slug": "general",
    "color": "#0000FF",
    "order_index": 0,
    "is_active": true,
    "created_at": "2026-02-15T12:00:00",
    "updated_at": "2026-02-15T12:00:00"
  }
]
```

### Create Category
```
POST /categories
```

**Authentication:** Required (Admin only)
**Request Body:**
```json
{
  "name": "Announcements",
  "slug": "announcements",
  "color": "#FF0000",
  "order_index": 1
}
```

**Response:** `201 Created`

### Update Category
```
PUT /categories/{category_id}
```

**Authentication:** Required (Admin only)
**Request Body:**
```json
{
  "name": "Updated Name",
  "is_active": false
}
```

**Response:** `200 OK`

### Delete Category
```
DELETE /categories/{category_id}
```

**Authentication:** Required (Admin only)
**Response:** `204 No Content`

---

## Posts

### List Posts
```
GET /posts
```

**Authentication:** Optional
**Query Parameters:**
- `page` (int, default: 1): Page number
- `limit` (int, default: 20, max: 100): Items per page
- `category_id` (UUID, optional): Filter by category
- `sort` (string, default: "recent"): Sorting method
  - `recent`: Most recent posts first
  - `popular`: Highest likes first
  - `trending`: Trending by engagement

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Post Title",
      "author": {
        "id": "uuid",
        "name": "John Doe",
        "picture": "https://...",
        "username": "johndoe"
      },
      "category_id": "uuid",
      "created_at": "2026-02-15T12:00:00",
      "updated_at": "2026-02-15T12:00:00",
      "view_count": 100,
      "like_count": 10,
      "comment_count": 5,
      "bookmark_count": 2,
      "is_liked": false,
      "is_bookmarked": false
    }
  ],
  "total": 50,
  "page": 1,
  "limit": 20,
  "pages": 3,
  "has_next": true,
  "has_prev": false
}
```

### Create Post
```
POST /posts
```

**Authentication:** Required
**Rate Limit:** 10 posts per minute per user

**Request Body:**
```json
{
  "title": "My First Post",
  "content": "Post content here",
  "category_id": "uuid",
  "tags": ["tag1", "tag2"],
  "status": "published"
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "title": "My First Post",
  "content": "Post content here",
  "author": { ... },
  "category_id": "uuid",
  "tags": ["tag1", "tag2"],
  "status": "published",
  "created_at": "2026-02-15T12:00:00",
  "updated_at": "2026-02-15T12:00:00",
  "view_count": 0,
  "like_count": 0,
  "comment_count": 0,
  "bookmark_count": 0,
  "is_liked": false,
  "is_bookmarked": false
}
```

### Get Post
```
GET /posts/{post_id}
```

**Authentication:** Optional
**Response:** `200 OK` (with full post details and incremented view_count)

**Errors:**
- `404 Not Found`: Post not found

### Update Post
```
PUT /posts/{post_id}
```

**Authentication:** Required (Author only)
**Request Body:** Same as Create Post (all fields optional)

**Response:** `200 OK`

**Errors:**
- `404 Not Found`: Post not found or not authorized
- `400 Bad Request`: Invalid data

### Delete Post
```
DELETE /posts/{post_id}
```

**Authentication:** Required (Author only)
**Response:** `204 No Content` (soft delete)

**Errors:**
- `404 Not Found`: Post not found or not authorized

### Search Posts
```
GET /search?q={query}
```

**Authentication:** Optional
**Query Parameters:**
- `q` (string, required, min 2 chars): Search query
- `page` (int, default: 1): Page number
- `limit` (int, default: 20, max: 100): Items per page

**Search Features:**
- **Primary:** PostgreSQL Full-Text Search (tsvector @@ plainto_tsquery)
- **Fallback:** Trigram similarity matching (pg_trgm)

**Response:** `200 OK` (same format as List Posts)

**Errors:**
- `400 Bad Request`: Query too short

---

## Comments

### Get Comments (Tree Structure)
```
GET /posts/{post_id}/comments
```

**Authentication:** Optional
**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "post_id": "uuid",
    "author": {
      "id": "uuid",
      "name": "Jane Smith",
      "picture": "https://...",
      "username": "janesmith"
    },
    "content": "Comment content",
    "depth": 0,
    "like_count": 3,
    "created_at": "2026-02-15T12:00:00",
    "updated_at": "2026-02-15T12:00:00",
    "replies": [
      {
        "id": "uuid",
        "post_id": "uuid",
        "author": { ... },
        "content": "Reply to comment",
        "depth": 1,
        "like_count": 1,
        "created_at": "2026-02-15T12:05:00",
        "updated_at": "2026-02-15T12:05:00",
        "replies": []
      }
    ]
  }
]
```

### Create Comment
```
POST /posts/{post_id}/comments
```

**Authentication:** Required
**Rate Limit:** 1 comment per second per user

**Request Body:**
```json
{
  "content": "My comment",
  "parent_comment_id": null
}
```

**Response:** `201 Created`

**Errors:**
- `429 Too Many Requests`: Rate limit exceeded
- `404 Not Found`: Post not found

### Create Reply (Answer to Comment)
```
POST /posts/{post_id}/comments/{comment_id}/replies
```

**Authentication:** Required
**Request Body:**
```json
{
  "content": "My reply"
}
```

**Response:** `201 Created`

**Note:** Maximum comment depth is 2 levels:
- Level 0: Top-level comments
- Level 1: Replies to top-level comments

**Errors:**
- `400 Bad Request`: Maximum comment depth exceeded
- `404 Not Found`: Parent comment not found

### Update Comment
```
PUT /comments/{comment_id}
```

**Authentication:** Required (Author only)
**Request Body:**
```json
{
  "content": "Updated comment"
}
```

**Response:** `200 OK`

**Errors:**
- `404 Not Found`: Comment not found or not authorized

### Delete Comment
```
DELETE /comments/{comment_id}
```

**Authentication:** Required (Author only)
**Response:** `204 No Content`

**Note:** Deleted comments are soft-deleted with content replaced by `[삭제됨]`

**Errors:**
- `404 Not Found`: Comment not found or not authorized

---

## Reactions

### Like Post
```
POST /posts/{post_id}/like
```

**Authentication:** Required
**Response:** `200 OK`

```json
{
  "post_id": "uuid",
  "is_liked": true,
  "like_count": 11
}
```

### Unlike Post
```
DELETE /posts/{post_id}/like
```

**Authentication:** Required
**Response:** `200 OK`

```json
{
  "post_id": "uuid",
  "is_liked": false,
  "like_count": 10
}
```

### Bookmark Post
```
POST /posts/{post_id}/bookmark
```

**Authentication:** Required
**Response:** `200 OK`

```json
{
  "post_id": "uuid",
  "is_bookmarked": true,
  "bookmark_count": 3
}
```

### Unbookmark Post
```
DELETE /posts/{post_id}/bookmark
```

**Authentication:** Required
**Response:** `200 OK`

```json
{
  "post_id": "uuid",
  "is_bookmarked": false,
  "bookmark_count": 2
}
```

### Like Comment
```
POST /comments/{comment_id}/like
```

**Authentication:** Required
**Response:** `200 OK`

```json
{
  "comment_id": "uuid",
  "is_liked": true,
  "like_count": 4
}
```

### Unlike Comment
```
DELETE /comments/{comment_id}/like
```

**Authentication:** Required
**Response:** `200 OK`

```json
{
  "comment_id": "uuid",
  "is_liked": false,
  "like_count": 3
}
```

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "success": false,
  "error": "Error message",
  "detail": "Optional detailed message",
  "code": "ERROR_CODE"
}
```

### Common Error Codes
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `400 Bad Request`: Invalid request data
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

## Rate Limiting

The API implements rate limiting for write operations:

| Operation | Limit | Window |
|---|---|---|
| Create Post | 10 | 1 minute |
| Create Comment | 1 | 1 second |

**Headers:**
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## Events

The Board System emits events to the event bus for integrations:

```python
# Post events
event_type="board.post.created"
event_type="board.post.updated"
event_type="board.post.deleted"
event_type="board.post.viewed"
event_type="board.post.liked"  # payload: { liked: bool }

# Comment events
event_type="board.comment.created"
event_type="board.comment.updated"
event_type="board.comment.deleted"
event_type="board.comment.liked"  # payload: { liked: bool }
```

---

## Database Schema

### board_categories
```sql
CREATE TABLE board_categories (
  id UUID PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  color VARCHAR(7) DEFAULT '#000000',
  order_index INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  is_deleted BOOLEAN DEFAULT false
)
```

### board_posts
```sql
CREATE TABLE board_posts (
  id UUID PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  content TEXT NOT NULL,
  status VARCHAR(20) DEFAULT 'published',
  author_id UUID NOT NULL REFERENCES users(id),
  category_id UUID REFERENCES board_categories(id),
  tags TEXT[] DEFAULT '{}',
  view_count INTEGER DEFAULT 0,
  like_count INTEGER DEFAULT 0,
  comment_count INTEGER DEFAULT 0,
  bookmark_count INTEGER DEFAULT 0,
  search_vector TSVECTOR,  -- Auto-updated by trigger
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  is_deleted BOOLEAN DEFAULT false
)
```

### comments
```sql
CREATE TABLE comments (
  id UUID PRIMARY KEY,
  post_id UUID NOT NULL REFERENCES board_posts(id),
  author_id UUID NOT NULL REFERENCES users(id),
  parent_comment_id UUID REFERENCES comments(id),
  content TEXT NOT NULL,
  depth INTEGER DEFAULT 0,  -- 0 = top-level, 1 = reply
  like_count INTEGER DEFAULT 0,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  is_deleted BOOLEAN DEFAULT false
)
```

### post_likes
```sql
CREATE TABLE post_likes (
  id UUID PRIMARY KEY,
  post_id UUID NOT NULL REFERENCES board_posts(id),
  user_id UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMP,
  UNIQUE(post_id, user_id)
)
```

### post_bookmarks
```sql
CREATE TABLE post_bookmarks (
  id UUID PRIMARY KEY,
  post_id UUID NOT NULL REFERENCES board_posts(id),
  user_id UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMP,
  UNIQUE(post_id, user_id)
)
```

### comment_likes
```sql
CREATE TABLE comment_likes (
  id UUID PRIMARY KEY,
  comment_id UUID NOT NULL REFERENCES comments(id),
  user_id UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMP,
  UNIQUE(comment_id, user_id)
)
```

---

## Example Workflows

### Create a Post with Comments

```bash
# 1. Create a post
curl -X POST http://localhost:8000/api/v1/board/posts \
  -H "X-API-Key: your-api-key" \
  -H "X-Platform: web" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Post",
    "content": "Post content",
    "category_id": "uuid",
    "tags": ["introduction"]
  }'

# Response: { "id": "post-uuid", ... }

# 2. Add a comment
curl -X POST http://localhost:8000/api/v1/board/posts/{post-uuid}/comments \
  -H "X-API-Key: your-api-key" \
  -H "X-Platform: web" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Great post!"
  }'

# Response: { "id": "comment-uuid", ... }

# 3. Reply to comment
curl -X POST http://localhost:8000/api/v1/board/posts/{post-uuid}/comments/{comment-uuid}/replies \
  -H "X-API-Key: your-api-key" \
  -H "X-Platform: web" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Thanks for the feedback!"
  }'

# 4. Like the post
curl -X POST http://localhost:8000/api/v1/board/posts/{post-uuid}/like \
  -H "X-API-Key: your-api-key" \
  -H "X-Platform: web" \
  -H "Authorization: Bearer {token}"

# Response: { "post_id": "post-uuid", "is_liked": true, "like_count": 1 }
```

### Search Posts

```bash
curl -X GET "http://localhost:8000/api/v1/board/search?q=python&page=1&limit=10" \
  -H "X-API-Key: your-api-key" \
  -H "X-Platform: web"

# Response: Paginated search results
```

---

## Security Considerations

1. **API Key Validation**: All endpoints require X-API-Key header
2. **Authentication**: Authenticated endpoints require valid Bearer token
3. **Authorization**: Users can only modify their own posts/comments
4. **Content Sanitization**: All user input is sanitized to prevent XSS
5. **Rate Limiting**: Write operations are rate-limited to prevent abuse
6. **Soft Delete**: Deleted posts/comments are soft-deleted, not permanently removed
7. **Deleted Content Masking**: Deleted comments show `[삭제됨]` instead of content

---

## Performance Notes

1. **Search Optimization**: Uses PostgreSQL Full-Text Search (FTS) with TSVECTOR index and trigram similarity fallback
2. **Pagination**: Recommended limit is 20-50 items per page
3. **Caching**: Category list is cacheable (includes ETag support)
4. **Indexing**: All foreign keys and frequently queried columns have indexes
5. **Async**: All database operations are non-blocking

---

## Versioning

API Version: **v1**
Last Updated: 2026-02-15

---

## Support

For issues or questions, please contact the development team or open an issue on the project repository.
