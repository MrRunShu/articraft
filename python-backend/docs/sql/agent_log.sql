-- 智能体执行日志表
CREATE TABLE IF NOT EXISTS agent_log
(
    id           BIGINT AUTO_INCREMENT COMMENT 'id' PRIMARY KEY,
    taskId       VARCHAR(64)  NOT NULL COMMENT '任务ID',
    agentName    VARCHAR(50)  NOT NULL COMMENT '智能体名称',
    startTime    DATETIME     NOT NULL COMMENT '开始时间',
    endTime      DATETIME     NULL COMMENT '结束时间',
    durationMs   INT          NULL COMMENT '耗时（毫秒）',
    status       VARCHAR(20)  NOT NULL COMMENT '状态：SUCCESS/FAILED',
    errorMessage TEXT         NULL COMMENT '错误信息',
    prompt       TEXT         NULL COMMENT '使用的 Prompt',
    inputData    JSON         NULL COMMENT '输入数据（JSON格式）',
    outputData   JSON         NULL COMMENT '输出数据（JSON格式）',
    createTime   DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间',
    updateTime   DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    isDelete     TINYINT      DEFAULT 0 NOT NULL COMMENT '是否删除',
    INDEX idx_taskId (taskId),
    INDEX idx_agentName (agentName),
    INDEX idx_status (status),
    INDEX idx_createTime (createTime)
) COMMENT '智能体执行日志表' COLLATE = utf8mb4_unicode_ci;
