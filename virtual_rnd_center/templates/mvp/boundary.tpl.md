# [LEAN_GATE] PROJECT BOUNDARY MANIFEST
## 1. Project Context
- **Product Name**: {{project_name}}
- **Primary Objective**: {{core_value_proposition}}
- **Target Audience**: (Specific segment defined during interview)

## 2. Iterative Pruning & Decision Traceability
| Iteration | Strategic Question | Stakeholder Decision | Impact on Architecture |
| :--- | :--- | :--- | :--- |
| Round 1 | ... | Yes / No | ... |
| Round 2 | ... | Yes / No | ... |
| Round 3 | ... | Yes / No | ... |

## 3. Scope Configuration
### 🟢 [X] IN SCOPE (Commitment for V1)
- **Core Feature 1**: (Description & Acceptance Criteria)
- **Core Feature 2**: (Description & Acceptance Criteria)
- **Essential Middleware**: (e.g., Local SQLite, Basic Auth)

### 🔴 [ ] OUT OF SCOPE (Deferred/Cut)
- **Feature X**: (Reason for pruning - e.g., "Too complex for MVP")
- **Scale Target**: (e.g., "Not optimized for >1000 CCU initially")

## 4. Constraint & Assumption Matrix
- **Resource Constraint**: (e.g., "Must run in a single container")
- **Assumed Knowledge**: (e.g., "User knows how to use a web browser")

## 5. BANNED FUNCTIONAL ENTITIES & IMPLEMENTATION PATHS
(明确定义在 V1 版本中绝对禁止在代码中实现的【业务功能实体】与【接口路径限制】。这些规则将作为 Code Reviewer 进行语义合规性评估的唯一黄金标准。
例如：
- 社交互动限制：禁止设计与实现任何处理"点赞(Likes)"、"评论(Comments)"、"分享(Shares)"、"好友关系(Friendship/Follow)"的 API 接口及数据库表结构。
- 媒体处理限制：禁止设计与实现任何文件上传(Upload)、多媒体资源云存储(OSS/S3)、头像上传(Avatar)相关的代码逻辑。)

## 6. Official Boundary Sign-off
- **Confidence Level**: [Low / Medium / High]
- **Gatekeeper**: AI Pruning Specialist
