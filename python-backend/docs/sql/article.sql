-- 文章表
CREATE TABLE IF NOT EXISTS article
(
    id             BIGINT AUTO_INCREMENT COMMENT 'id' PRIMARY KEY,
    taskId         VARCHAR(64)  NOT NULL COMMENT '任务ID（UUID）',
    userId         BIGINT       NOT NULL COMMENT '用户ID',
    topic          VARCHAR(500) NOT NULL COMMENT '选题',
    mainTitle      VARCHAR(200)          COMMENT '主标题',
    subTitle       VARCHAR(300)          COMMENT '副标题',
    outline        TEXT                  COMMENT '大纲（JSON格式）',
    content        TEXT                  COMMENT '正文（Markdown格式）',
    fullContent    TEXT                  COMMENT '完整图文（Markdown格式，含配图）',
    coverImage     VARCHAR(512)          COMMENT '封面图 URL',
    images         TEXT                  COMMENT '配图列表（JSON数组）',
    status         VARCHAR(20)  NOT NULL DEFAULT 'PENDING' COMMENT '状态：PENDING/PROCESSING/COMPLETED/FAILED',
    errorMessage   TEXT                  COMMENT '错误信息',
    createTime     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    completedTime  DATETIME              COMMENT '完成时间',
    updateTime     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    isDelete       TINYINT      NOT NULL DEFAULT 0 COMMENT '是否删除',
    UNIQUE KEY uk_taskId (taskId),
    INDEX idx_userId (userId),
    INDEX idx_status (status),
    INDEX idx_createTime (createTime)
) COMMENT '文章表' COLLATE = utf8mb4_unicode_ci;
