"""
OKAMI FastAPIサーバー
OKAMIシステムのメインエントリーポイント
"""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Response
from pydantic import BaseModel, Field
import time
from datetime import datetime
from pathlib import Path

from utils.logger import initialize_logger, get_logger
from utils.config import get_config
from monitoring.claude_quality_monitor import ClaudeQualityMonitor, ResponseQuality
from crewai import Crew, Agent, Task
from crews import CrewFactory
from evolution.improvement_parser import ImprovementParser
from evolution.improvement_applier import ImprovementApplier

# ロギングの初期化
logger = initialize_logger()
app_logger = get_logger(__name__)

# 設定の初期化
config = get_config()

# 品質監視用のタスク実行履歴
task_history: Dict[str, Dict[str, Any]] = {}

# 改善指示のキュー
improvement_queue: List[Dict[str, Any]] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフスパンマネージャー"""
    # 起動時
    app_logger.info("OKAMI system starting up", version="0.1.0")
    
    # システム情報のログ
    app_logger.info(
        "System initialized",
        environment=os.getenv("ENVIRONMENT", "production"),
        storage_dir=config.crewai_storage_dir
    )
    
    yield
    
    # シャットダウン時
    app_logger.info("OKAMI system shutting down")


# FastAPIアプリの作成
app = FastAPI(
    title="OKAMI - Orchestrated Knowledge-driven Autonomous Multi-agent Intelligence",
    description="CrewAIによる自己進化型AIエージェントシステム",
    version="0.1.0",
    lifespan=lifespan
)

# CORSミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルのマウント
static_path = Path(__file__).parent / "webui" / "public"
if static_path.exists():
    app.mount("/public", StaticFiles(directory=static_path), name="static")

# webui_distパスの初期化
webui_dist = Path(__file__).parent / "webui" / "dist"


# リクエスト/レスポンスモデル
class TaskRequest(BaseModel):
    """タスク実行リクエスト"""
    crew_name: str = Field(default="main_crew", description="実行するクルーの名前")
    task: str = Field(..., description="タスクの説明")
    context: Optional[Dict[str, Any]] = Field(None, description="タスクコンテキスト")
    inputs: Optional[Dict[str, Any]] = Field(None, description="タスク入力")
    async_execution: bool = Field(False, description="非同期実行")


class TaskResponse(BaseModel):
    """タスク実行レスポンス"""
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class SystemStatus(BaseModel):
    """システムステータスレスポンス"""
    status: str
    active_crews: int
    total_tasks: int
    recent_quality_score: float
    pending_improvements: int


class ImprovementInstruction(BaseModel):
    """改善指示"""
    target: str = Field(..., description="ターゲットコンポーネント")
    improvements: List[Dict[str, Any]] = Field(..., description="改善リスト")
    priority: str = Field(default="medium", description="優先度レベル")


# クルーファクトリーインスタンス
crew_factory = CrewFactory()

# 進化改善プロセッサー
improvement_parser = ImprovementParser()
improvement_applier = ImprovementApplier()


@app.get("/api", tags=["System"])
async def api_root():
    """APIルートエンドポイント"""
    return {
        "name": "OKAMI System API",
        "version": "0.1.0",
        "status": "operational",
        "description": "オーケストレートされた知識駆動型自律マルチエージェントインテリジェンス"
    }


@app.get("/health", tags=["System"])
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # 基本的なヘルスチェック
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "api": "healthy",
                "crews": "healthy",
                "monitoring": "healthy"
            }
        }
        
        return health_status
    except Exception as e:
        app_logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/status", response_model=SystemStatus, tags=["System"])
async def get_system_status():
    """システムステータスを取得"""
    try:
        # アクティブなクルーを取得
        active_crews = crew_factory.get_active_crews()
        
        # 最近の品質スコアを計算
        recent_tasks = [
            task for task in task_history.values()
            if task.get("timestamp") and 
            (datetime.utcnow() - task["timestamp"]).seconds < 3600
        ]
        
        quality_scores = []
        for task in recent_tasks:
            if "quality_score" in task:
                quality_scores.append(task["quality_score"])
        
        avg_quality_score = (
            sum(quality_scores) / len(quality_scores) 
            if quality_scores else 0.0
        )
        
        return SystemStatus(
            status="healthy",
            active_crews=len(active_crews),
            total_tasks=len(task_history),
            recent_quality_score=avg_quality_score,
            pending_improvements=len(improvement_queue)
        )
        
    except Exception as e:
        app_logger.error("Failed to get system status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/recent", tags=["Tasks"])
async def get_recent_tasks(limit: int = 10):
    """最近のタスク実行を取得"""
    try:
        # タイムスタンプでタスクをソート
        sorted_tasks = sorted(
            task_history.items(),
            key=lambda x: x[1].get("timestamp", datetime.min),
            reverse=True
        )
        
        # 制限された結果を返す
        recent_tasks = []
        for task_id, task_data in sorted_tasks[:limit]:
            recent_tasks.append({
                "task_id": task_id,
                "status": task_data.get("status"),
                "execution_time": task_data.get("execution_time"),
                "task_description": task_data.get("task_description"),
                "expected_output": task_data.get("expected_output"),
                "result": task_data.get("result"),
                "timestamp": task_data.get("timestamp"),
                "quality_score": task_data.get("quality_score")
            })
        
        return recent_tasks
        
    except Exception as e:
        app_logger.error("Failed to get recent tasks", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks", response_model=TaskResponse, tags=["Tasks"])
async def execute_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks
):
    """タスクを実行"""
    try:
        task_id = f"task_{int(time.time() * 1000)}"
        
        app_logger.info(
            "Task execution requested",
            task_id=task_id,
            crew_name=request.crew_name,
            async_execution=request.async_execution
        )
        
        # クルーを取得または作成
        crew = crew_factory.get_crew(request.crew_name)
        if not crew:
            raise HTTPException(status_code=404, detail=f"Crew not found: {request.crew_name}")
        
        # タスク情報を保存
        task_history[task_id] = {
            "task_id": task_id,
            "crew_name": request.crew_name,
            "task_description": request.task,
            "expected_output": "タスク要件に対応した包括的なレスポンス",
            "status": "processing",
            "timestamp": datetime.utcnow()
        }
        
        # 入力を準備
        inputs = request.inputs or {}
        inputs["task"] = request.task
        if request.context:
            inputs["context"] = request.context
        
        if request.async_execution:
            # バックグラウンドで実行
            background_tasks.add_task(
                _execute_task_async,
                task_id,
                crew,
                inputs
            )
            
            return TaskResponse(
                task_id=task_id,
                status="processing",
                result=None
            )
        else:
            # 同期的に実行
            start_time = time.time()
            
            try:
                result = crew.kickoff(inputs=inputs)
                execution_time = time.time() - start_time
                
                # タスク履歴を更新
                task_history[task_id].update({
                    "status": "completed",
                    "result": result,
                    "execution_time": execution_time,
                    "quality_score": 0.85  # プレースホルダー - モニターによって計算される
                })
                
                app_logger.info(
                    "Task completed",
                    task_id=task_id,
                    execution_time=execution_time
                )
                
                # main_crewが正常に完了した場合、バックグラウンドでevolution_crewをトリガー
                if request.crew_name == "main_crew":
                    background_tasks.add_task(
                        _trigger_evolution_analysis,
                        task_id=task_id,
                        task_result=result,
                        task_description=request.task
                    )
                
                return TaskResponse(
                    task_id=task_id,
                    status="completed",
                    result=result,
                    execution_time=execution_time
                )
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                # タスク履歴を更新
                task_history[task_id].update({
                    "status": "failed",
                    "error": str(e),
                    "execution_time": execution_time,
                    "quality_score": 0.0
                })
                
                app_logger.error(
                    "Task execution failed",
                    task_id=task_id,
                    error=str(e)
                )
                
                return TaskResponse(
                    task_id=task_id,
                    status="failed",
                    error=str(e),
                    execution_time=execution_time
                )
    
    except Exception as e:
        app_logger.error("Failed to process task request", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def _trigger_evolution_analysis(task_id: str, task_result: Any, task_description: str):
    """main crew完了後にevolution crew分析をトリガー"""
    try:
        app_logger.info(
            "Triggering evolution analysis",
            original_task_id=task_id
        )
        
        # 進化タスクを準備
        evolution_inputs = {
            "task": f"""Analyze the following task execution and provide improvement recommendations:
            
            Original Task: {task_description}
            Task Result: {str(task_result)[:1000]}  # サイズ制限
            
            Please analyze:
            1. Task execution efficiency
            2. Response quality
            3. Agent coordination
            4. Knowledge gaps
            5. Process improvements
            
            Provide specific, actionable recommendations for:
            - Knowledge file updates
            - YAML configuration improvements
            - Agent prompt optimizations
            - Tool usage enhancements
            """
        }
        
        # 進化クルーを取得
        evolution_crew = crew_factory.get_crew("evolution_crew")
        if not evolution_crew:
            app_logger.error("Evolution crew not found")
            return
        
        # 進化分析を実行
        evolution_task_id = f"evolution_{task_id}"
        task_history[evolution_task_id] = {
            "task_id": evolution_task_id,
            "crew_name": "evolution_crew",
            "task_description": evolution_inputs["task"],
            "status": "processing",
            "timestamp": datetime.utcnow(),
            "parent_task_id": task_id
        }
        
        start_time = time.time()
        try:
            evolution_result = evolution_crew.kickoff(inputs=evolution_inputs)
            execution_time = time.time() - start_time
            
            task_history[evolution_task_id].update({
                "status": "completed",
                "result": evolution_result,
                "execution_time": execution_time
            })
            
            # 改善を処理して適用
            await _apply_evolution_improvements(evolution_result)
            
            app_logger.info(
                "Evolution analysis completed",
                evolution_task_id=evolution_task_id,
                execution_time=execution_time
            )
            
        except Exception as e:
            task_history[evolution_task_id].update({
                "status": "failed",
                "error": str(e),
                "execution_time": time.time() - start_time
            })
            app_logger.error(
                "Evolution analysis failed",
                evolution_task_id=evolution_task_id,
                error=str(e)
            )
            
    except Exception as e:
        app_logger.error(
            "Failed to trigger evolution analysis",
            error=str(e)
        )


async def _apply_evolution_improvements(evolution_result: Any):
    """進化クルーが提案した改善を適用"""
    try:
        # 進化結果を解析
        if hasattr(evolution_result, 'raw'):
            result_text = evolution_result.raw
        else:
            result_text = str(evolution_result)
        
        # 生の改善をログ
        improvement_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "improvements": result_text,
            "applied": False
        }
        
        improvement_queue.append(improvement_data)
        
        app_logger.info(
            "Evolution improvements received",
            length=len(result_text)
        )
        
        # 改善を構造化された形式に解析
        parsed_improvements = improvement_parser.parse_improvements(result_text)
        
        # 実行可能な変更に変換
        actionable_changes = improvement_parser.extract_actionable_changes(parsed_improvements)
        
        if actionable_changes:
            app_logger.info(
                "Applying evolution improvements",
                changes=len(actionable_changes)
            )
            
            # 変更を適用（dry_run=Falseで実際に変更を行う）
            results = improvement_applier.apply_changes(actionable_changes, dry_run=False)
            
            # 結果で改善データを更新
            improvement_data["parsed"] = parsed_improvements
            improvement_data["results"] = results
            improvement_data["applied"] = len(results.get("applied", [])) > 0
            
            app_logger.info(
                "Evolution improvements applied",
                applied=len(results.get("applied", [])),
                failed=len(results.get("failed", [])),
                skipped=len(results.get("skipped", []))
            )
            
            # 重要なファイルが更新された場合、設定を再読み込み
            critical_files = ["agents", "tasks", "crews"]
            if any(any(crit in str(change[0]) for crit in critical_files) 
                   for change in actionable_changes):
                crew_factory.reload_configs()
                app_logger.info("Configurations reloaded due to evolution updates")
        else:
            app_logger.info("No actionable improvements found in evolution result")
        
    except Exception as e:
        app_logger.error(
            "Failed to apply evolution improvements",
            error=str(e),
            exc_info=True
        )


async def _execute_task_async(task_id: str, crew: Crew, inputs: Dict[str, Any]):
    """タスクを非同期で実行"""
    start_time = time.time()
    
    try:
        result = await crew.kickoff_async(inputs=inputs)
        execution_time = time.time() - start_time
        
        # Update task history
        task_history[task_id].update({
            "status": "completed",
            "result": result,
            "execution_time": execution_time,
            "quality_score": 0.85  # プレースホルダー
        })
        
        app_logger.info(
            "Async task completed",
            task_id=task_id,
            execution_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        
        # Update task history
        task_history[task_id].update({
            "status": "failed",
            "error": str(e),
            "execution_time": execution_time,
            "quality_score": 0.0
        })
        
        app_logger.error(
            "Async task failed",
            task_id=task_id,
            error=str(e)
        )


@app.post("/improvements", tags=["Quality"])
async def receive_improvement(instruction: ImprovementInstruction):
    """Claude Monitorから改善指示を受信"""
    try:
        # キューに追加
        improvement_data = {
            "timestamp": datetime.utcnow(),
            "target": instruction.target,
            "improvements": instruction.improvements,
            "priority": instruction.priority,
            "applied": False
        }
        
        improvement_queue.append(improvement_data)
        
        # ターゲットに基づいて改善を適用
        if instruction.target == "crew_optimization":
            _apply_crew_optimization(instruction.improvements)
        elif instruction.target == "agent_instructions":
            _apply_agent_improvements(instruction.improvements)
        
        app_logger.info(
            "Improvement instruction received",
            target=instruction.target,
            improvement_count=len(instruction.improvements)
        )
        
        return {"status": "received", "queued_improvements": len(improvement_queue)}
        
    except Exception as e:
        app_logger.error("Failed to process improvement", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


def _apply_crew_optimization(improvements: List[Dict[str, Any]]):
    """クルー最適化改善を適用"""
    for improvement in improvements:
        suggestions = improvement.get("suggestions", [])
        
        for suggestion in suggestions:
            if "caching" in suggestion.lower():
                # すべてのクルーにキャッシュを有効化
                for crew in crew_factory.get_active_crews().values():
                    crew.cache = True
                app_logger.info("Enabled caching for all crews")
            
            elif "parallelize" in suggestion.lower():
                # これはクルー固有の実装が必要
                app_logger.info("Parallelization improvement noted for future implementation")


def _apply_agent_improvements(improvements: List[Dict[str, Any]]):
    """エージェント固有の改善を適用"""
    for improvement in improvements:
        issues = improvement.get("issues", [])
        suggestions = improvement.get("suggestions", [])
        
        # 手動レビューと実装のためにログ
        app_logger.info(
            "Agent improvements identified",
            issues=issues,
            suggestions=suggestions
        )
        
        # 実際の実装では以下を行う:
        # 1. エージェントプロンプトの更新
        # 2. エージェント設定の調整
        # 3. タスク定義の変更


@app.get("/improvements", tags=["Quality"])
async def get_improvements():
    """保留中の改善を取得"""
    try:
        # 最近の改善を取得
        recent_improvements = [
            imp for imp in improvement_queue
            if not imp.get("applied", False)
        ][-20:]  # 未適用の最後の20件の改善
        
        return {
            "total_improvements": len(improvement_queue),
            "pending_improvements": len(recent_improvements),
            "improvements": recent_improvements
        }
        
    except Exception as e:
        app_logger.error("Failed to get improvements", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/improvements/apply/{improvement_id}", tags=["Quality"])
async def apply_improvement(improvement_id: int):
    """特定の改善を手動で適用"""
    try:
        if improvement_id >= len(improvement_queue):
            raise HTTPException(status_code=404, detail="Improvement not found")
        
        improvement = improvement_queue[improvement_id]
        
        if improvement.get("applied"):
            return {"status": "already_applied"}
        
        # 改善を解析して適用
        result_text = improvement.get("improvements", "")
        parsed = improvement_parser.parse_improvements(result_text)
        changes = improvement_parser.extract_actionable_changes(parsed)
        
        if changes:
            results = improvement_applier.apply_changes(changes, dry_run=False)
            improvement["results"] = results
            improvement["applied"] = True
            
            # 必要に応じて設定を再読み込み
            if any("config/" in str(change[0]) for change in changes):
                crew_factory.reload_configs()
            
            return {
                "status": "applied",
                "results": results
            }
        else:
            return {"status": "no_changes"}
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error("Failed to apply improvement", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/improvements/history", tags=["Quality"])
async def get_improvement_history(limit: int = 50):
    """改善適用履歴を取得"""
    try:
        # 結果を持つすべての改善を取得
        history = []
        for i, imp in enumerate(improvement_queue):
            if "results" in imp:
                history.append({
                    "id": i,
                    "timestamp": imp.get("timestamp"),
                    "applied": imp.get("applied", False),
                    "summary": {
                        "applied": len(imp["results"].get("applied", [])),
                        "failed": len(imp["results"].get("failed", [])),
                        "skipped": len(imp["results"].get("skipped", []))
                    },
                    "details": imp.get("results")
                })
        
        # タイムスタンプの降順でソート
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "total": len(history),
            "history": history[:limit]
        }
        
    except Exception as e:
        app_logger.error("Failed to get improvement history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/crews", tags=["Crews"])
async def get_crews():
    """利用可能なクルーを取得"""
    try:
        crews = crew_factory.list_crews()
        return {"crews": crews}
    except Exception as e:
        app_logger.error("Failed to get crews", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/crews/{crew_name}", tags=["Crews"])
async def get_crew_info(crew_name: str):
    """クルー情報を取得"""
    try:
        crew = crew_factory.get_crew(crew_name)
        if not crew:
            raise HTTPException(status_code=404, detail=f"Crew not found: {crew_name}")
        
        return {
            "name": crew.name,
            "agents": [agent.role for agent in crew.agents],
            "tasks": [task.description[:100] + "..." for task in crew.tasks],
            "process": str(crew.process),
            "memory_enabled": hasattr(crew, 'memory_manager'),
            "knowledge_enabled": hasattr(crew, 'knowledge_manager')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error("Failed to get crew info", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents", tags=["Agents"])
async def get_agents():
    """利用可能なエージェントを取得"""
    try:
        agents = crew_factory.list_agents()
        agent_details = []
        
        for agent_name in agents:
            agent_config = crew_factory.agent_configs.get(agent_name, {})
            agent_details.append({
                "name": agent_name,
                "role": agent_config.get("role", "Unknown"),
                "goal": agent_config.get("goal", ""),
                "backstory": agent_config.get("backstory", ""),
                "tools": agent_config.get("tools", []),
                "memory": agent_config.get("memory", True),
                "max_iter": agent_config.get("max_iter", 10)
            })
        
        return {"agents": agent_details}
    except Exception as e:
        app_logger.error("Failed to get agents", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks", tags=["Tasks"])
async def get_tasks():
    """すべてのタスクを取得"""
    try:
        return {"tasks": list(task_history.values())}
    except Exception as e:
        app_logger.error("Failed to get tasks", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}", tags=["Tasks"])
async def get_task(task_id: str):
    """特定のタスク詳細を取得"""
    try:
        if task_id not in task_history:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        return task_history[task_id]
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error("Failed to get task", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring", tags=["Monitoring"])
async def get_monitoring():
    """モニタリングデータを取得"""
    try:
        # メトリクスを計算
        total_tasks = len(task_history)
        completed_tasks = len([t for t in task_history.values() if t.get("status") == "completed"])
        failed_tasks = len([t for t in task_history.values() if t.get("status") == "failed"])
        
        avg_execution_time = 0
        if completed_tasks > 0:
            execution_times = [t.get("execution_time", 0) for t in task_history.values() if t.get("execution_time")]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "avg_execution_time": avg_execution_time,
            "pending_improvements": len(improvement_queue)
        }
    except Exception as e:
        app_logger.error("Failed to get monitoring data", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """グローバル例外ハンドラー"""
    app_logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=exc
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if config.okami_log_level == "DEBUG" else "予期しないエラーが発生しました"
        }
    )


# チャットHTML UIを提供
chat_ui_path = Path(__file__).parent / "webui" / "chat.html"
if chat_ui_path.exists():
    @app.get("/", response_class=FileResponse)
    async def serve_app():
        return FileResponse(chat_ui_path)


if __name__ == "__main__":
    # サーバーを実行
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        reload=config.server_reload,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": config.okami_log_level,
                "handlers": ["default"],
            },
        }
    )