"""
Production Orchestration Service

This module provides a production-ready orchestration service that integrates all components:
rules engine, event-driven orchestrator, template engine, notification system, and metrics.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from src.contexts.debate.aggregates import DebateSession
from src.contexts.debate.value_objects import Topic
from src.events.event_bus import EventBus, get_event_bus
from src.orchestration.event_driven_orchestrator import EventDrivenOrchestrator
from src.orchestration.template_engine import TemplateRegistry, get_template_registry, TemplateType
from src.orchestration.notification_system import create_notification_system, ParticipantNotificationManager
from src.orchestration.orchestration_metrics import get_metrics_collector, initialize_metrics
from src.orchestration.admin_interface import create_admin_app
from src.workflows.debate_workflow import WorkflowEngine

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationConfig:
    """Configuration for production orchestration service."""
    # Storage paths
    template_storage_path: Path = field(default_factory=lambda: Path("data/templates"))
    metrics_export_path: Path = field(default_factory=lambda: Path("data/orchestration_metrics"))
    
    # Feature flags
    enable_notifications: bool = True
    enable_metrics_export: bool = True
    enable_admin_interface: bool = True
    enable_auto_scaling: bool = False
    
    # Performance settings
    max_concurrent_debates: int = 10
    notification_batch_size: int = 50
    metrics_export_interval_minutes: int = 5
    
    # Timeouts and limits
    debate_timeout_minutes: int = 30
    notification_timeout_seconds: int = 10
    max_retry_attempts: int = 3
    
    # Monitoring
    enable_health_checks: bool = True
    health_check_interval_seconds: int = 30
    alert_threshold_error_rate: float = 0.1  # 10% error rate triggers alert
    
    # Debug settings
    log_level: str = "INFO"
    enable_debug_mode: bool = False


@dataclass
class SystemHealth:
    """System health status."""
    overall_status: str  # "healthy", "degraded", "unhealthy"
    active_debates: int
    pending_notifications: int
    error_rate: float
    avg_response_time_ms: float
    uptime_hours: float
    memory_usage_mb: float
    cpu_usage_percent: float
    last_check: datetime
    issues: List[str] = field(default_factory=list)


class ProductionOrchestrationService:
    """Production-ready orchestration service."""
    
    def __init__(self, config: Optional[OrchestrationConfig] = None, ai_client_factory=None):
        self.config = config or OrchestrationConfig()
        self.ai_client_factory = ai_client_factory
        
        # Core components
        self.event_bus = get_event_bus()
        self.template_registry = get_template_registry()
        self.metrics_collector = get_metrics_collector()
        self.orchestrator: Optional[EventDrivenOrchestrator] = None
        self.notification_manager: Optional[ParticipantNotificationManager] = None
        self.workflow_engine: Optional[WorkflowEngine] = None
        
        # State management
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.active_debates: Dict[UUID, DebateSession] = {}
        self.performance_metrics: Dict[str, float] = {}
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._metrics_export_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        if self.config.enable_debug_mode:
            logger.setLevel(logging.DEBUG)
    
    async def initialize(self):
        """Initialize all components and prepare for operation."""
        logger.info("Initializing production orchestration service...")
        
        try:
            # Initialize metrics system
            initialize_metrics(
                enable_file_export=self.config.enable_metrics_export,
                export_path=self.config.metrics_export_path
            )
            
            # Initialize template registry
            self.template_registry = TemplateRegistry(
                storage_path=self.config.template_storage_path
            )
            
            # Initialize notification system
            if self.config.enable_notifications:
                notification_scheduler, notification_manager = create_notification_system(self.event_bus)
                self.notification_manager = notification_manager
                await notification_scheduler.start()
                logger.info("Notification system initialized")
            
            # Initialize event-driven orchestrator
            self.orchestrator = EventDrivenOrchestrator(
                event_bus=self.event_bus,
                ai_client_factory=self.ai_client_factory
            )
            
            # Register templates with orchestrator
            for template in self.template_registry.list_templates():
                workflow_def = template.to_workflow_definition()
                self.orchestrator.register_template(workflow_def)
            
            # Initialize workflow engine
            self.workflow_engine = WorkflowEngine(self.event_bus)
            
            # Register workflow definitions
            for template in self.template_registry.list_templates():
                workflow_def = template.to_workflow_definition()
                self.workflow_engine.register_workflow_definition(workflow_def)
            
            logger.info("Production orchestration service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestration service: {e}")
            raise
    
    async def start(self):
        """Start the orchestration service."""
        if self.is_running:
            logger.warning("Service is already running")
            return
        
        logger.info("Starting production orchestration service...")
        
        try:
            await self.initialize()
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Record startup metrics
            self.metrics_collector.record_metric(
                "service_startups", 1, "counter"
            )
            
            logger.info("Production orchestration service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start orchestration service: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop the orchestration service."""
        if not self.is_running:
            return
        
        logger.info("Stopping production orchestration service...")
        
        try:
            self.is_running = False
            
            # Stop background tasks
            await self._stop_background_tasks()
            
            # Complete active debates
            for debate_id, debate_session in list(self.active_debates.items()):
                await self._complete_debate(debate_session, "service_shutdown")
            
            # Stop orchestrator
            if self.orchestrator:
                await self.orchestrator.shutdown()
            
            # Stop notification system
            if self.notification_manager:
                await self.notification_manager.scheduler.stop()
            
            # Record shutdown metrics
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            self.metrics_collector.record_metric(
                "service_uptime_seconds", uptime, "gauge"
            )
            
            logger.info("Production orchestration service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping orchestration service: {e}")
            raise
    
    async def start_debate(
        self,
        question: str,
        complexity: str = "moderate",
        template_id: Optional[str] = None,
        participants: Optional[List[str]] = None
    ) -> UUID:
        """Start a new debate."""
        if not self.is_running:
            raise RuntimeError("Service is not running")
        
        if len(self.active_debates) >= self.config.max_concurrent_debates:
            raise RuntimeError(f"Maximum concurrent debates ({self.config.max_concurrent_debates}) reached")
        
        logger.info(f"Starting debate: {question[:50]}...")
        
        # Select template
        if not template_id:
            template_id = self._select_optimal_template(complexity)
        
        template = self.template_registry.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Create debate session
        debate_id = uuid4()
        topic = Topic(question)
        
        debate_participants = participants or [p.id for p in template.participants]
        
        debate_session = DebateSession(
            id=debate_id,
            topic=topic,
            participants=debate_participants,
            max_rounds=template.workflow_config.max_rounds
        )
        
        self.active_debates[debate_id] = debate_session
        
        # Register participants for notifications
        if self.notification_manager:
            for participant_config in template.participants:
                self.notification_manager.register_participant(participant_config)
        
        # Start orchestration
        if self.orchestrator:
            orchestration_session = await self.orchestrator.start_orchestration(
                debate_session, question, complexity
            )
        
        # Start workflow execution
        if self.workflow_engine:
            asyncio.create_task(
                self._execute_debate_workflow(debate_session, template_id, question, complexity)
            )
        
        # Record metrics
        self.metrics_collector.start_debate_tracking(
            debate_id,
            set(debate_participants)
        )
        
        logger.info(f"Started debate {debate_id} with template {template_id}")
        return debate_id
    
    async def _execute_debate_workflow(
        self,
        debate_session: DebateSession,
        template_id: str,
        question: str,
        complexity: str
    ):
        """Execute debate workflow in background."""
        try:
            if not self.workflow_engine:
                logger.error("Workflow engine not initialized")
                return
            
            result = await self.workflow_engine.execute_workflow(
                template_id,
                question,
                complexity,
                ai_client_factory=self.ai_client_factory,
                orchestrator=self.orchestrator
            )
            
            # Update debate session with result
            if result.decision:
                debate_session.make_decision(result.decision)
            
            if result.consensus:
                debate_session.reach_consensus(result.consensus)
            
            # Complete debate
            await self._complete_debate(debate_session, "workflow_completed")
            
        except Exception as e:
            logger.error(f"Error executing debate workflow for {debate_session.id}: {e}")
            await self._complete_debate(debate_session, "workflow_error")
    
    async def _complete_debate(self, debate_session: DebateSession, reason: str):
        """Complete a debate and clean up."""
        debate_id = debate_session.id
        
        logger.info(f"Completing debate {debate_id}: {reason}")
        
        # Remove from active debates
        if debate_id in self.active_debates:
            del self.active_debates[debate_id]
        
        # End metrics tracking
        consensus_reached = debate_session.consensus is not None
        consensus_confidence = debate_session.consensus.confidence if debate_session.consensus else 0.0
        
        self.metrics_collector.end_debate_tracking(
            debate_id,
            completed_successfully=(reason != "workflow_error"),
            consensus_reached=consensus_reached,
            consensus_confidence=consensus_confidence
        )
    
    def _select_optimal_template(self, complexity: str) -> str:
        """Select the optimal template based on complexity."""
        if complexity == "simple":
            return "simple_debate"
        elif complexity == "complex":
            return "complex_debate"
        else:
            return "standard_debate"
    
    async def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks."""
        if self.config.enable_health_checks:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        if self.config.enable_metrics_export:
            self._metrics_export_task = asyncio.create_task(self._metrics_export_loop())
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Background tasks started")
    
    async def _stop_background_tasks(self):
        """Stop all background tasks."""
        tasks = [
            self._health_check_task,
            self._metrics_export_task,
            self._cleanup_task
        ]
        
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Background tasks stopped")
    
    async def _health_check_loop(self):
        """Background health checking loop."""
        while self.is_running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.config.health_check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.config.health_check_interval_seconds)
    
    async def _metrics_export_loop(self):
        """Background metrics export loop."""
        while self.is_running:
            try:
                self.metrics_collector.export_metrics()
                await asyncio.sleep(self.config.metrics_export_interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics export loop: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while self.is_running:
            try:
                await self._perform_cleanup()
                await asyncio.sleep(3600)  # Run every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def _perform_health_check(self):
        """Perform system health check."""
        try:
            import psutil
            
            # Get system metrics
            memory_usage = psutil.virtual_memory().used / (1024 * 1024)  # MB
            cpu_usage = psutil.cpu_percent()
            
            # Get service metrics
            uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600 if self.start_time else 0
            active_debates = len(self.active_debates)
            pending_notifications = 0
            
            if self.notification_manager:
                pending_notifications = len(self.notification_manager.scheduler.pending_notifications)
            
            # Calculate error rate
            total_operations = self.metrics_collector.counters.get('total_operations', 1)
            errors = self.metrics_collector.counters.get('errors', 0)
            error_rate = errors / total_operations if total_operations > 0 else 0
            
            # Determine overall status
            issues = []
            status = "healthy"
            
            if error_rate > self.config.alert_threshold_error_rate:
                issues.append(f"High error rate: {error_rate:.2%}")
                status = "degraded"
            
            if active_debates >= self.config.max_concurrent_debates:
                issues.append("At maximum concurrent debate limit")
                status = "degraded"
            
            if memory_usage > 1024:  # 1GB
                issues.append(f"High memory usage: {memory_usage:.1f}MB")
                status = "degraded"
            
            if cpu_usage > 80:
                issues.append(f"High CPU usage: {cpu_usage:.1f}%")
                status = "degraded"
            
            # Create health status
            health = SystemHealth(
                overall_status=status,
                active_debates=active_debates,
                pending_notifications=pending_notifications,
                error_rate=error_rate,
                avg_response_time_ms=self.performance_metrics.get('avg_response_time', 0),
                uptime_hours=uptime_hours,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                last_check=datetime.now(),
                issues=issues
            )
            
            # Record health metrics
            self.metrics_collector.record_metric("health_status", 1 if status == "healthy" else 0, "gauge")
            self.metrics_collector.record_metric("active_debates", active_debates, "gauge")
            self.metrics_collector.record_metric("memory_usage_mb", memory_usage, "gauge")
            self.metrics_collector.record_metric("cpu_usage_percent", cpu_usage, "gauge")
            
            # Log issues
            if issues:
                logger.warning(f"Health check issues: {', '.join(issues)}")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _perform_cleanup(self):
        """Perform system cleanup."""
        try:
            # Clean old metrics data
            self.metrics_collector.clear_old_data(days_to_keep=7)
            
            # Check for stale debates
            now = datetime.now()
            timeout = timedelta(minutes=self.config.debate_timeout_minutes)
            
            stale_debates = []
            for debate_id, debate_session in self.active_debates.items():
                # Check if debate has been running too long
                if hasattr(debate_session, 'start_time'):
                    if now - debate_session.start_time > timeout:
                        stale_debates.append((debate_id, debate_session))
            
            # Complete stale debates
            for debate_id, debate_session in stale_debates:
                logger.warning(f"Completing stale debate {debate_id}")
                await self._complete_debate(debate_session, "timeout")
            
            logger.debug(f"Cleanup completed. Cleaned {len(stale_debates)} stale debates")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        if not self.start_time:
            return {"status": "not_started"}
        
        uptime = datetime.now() - self.start_time
        metrics = self.metrics_collector.get_summary_stats()
        
        return {
            "status": "running" if self.is_running else "stopped",
            "uptime_seconds": uptime.total_seconds(),
            "active_debates": len(self.active_debates),
            "total_templates": len(self.template_registry.templates),
            "metrics": metrics,
            "config": {
                "max_concurrent_debates": self.config.max_concurrent_debates,
                "notifications_enabled": self.config.enable_notifications,
                "metrics_export_enabled": self.config.enable_metrics_export,
                "debug_mode": self.config.enable_debug_mode
            }
        }
    
    def get_active_debates(self) -> List[Dict[str, Any]]:
        """Get information about active debates."""
        debates = []
        for debate_id, debate_session in self.active_debates.items():
            debates.append({
                "id": str(debate_id),
                "topic": debate_session.topic.value,
                "participants": debate_session.participants,
                "rounds": len(debate_session.rounds),
                "max_rounds": debate_session.max_rounds,
                "has_consensus": debate_session.consensus is not None,
                "has_decision": debate_session.decision is not None
            })
        return debates
    
    def get_admin_app(self):
        """Get the admin interface FastAPI app."""
        if not self.config.enable_admin_interface:
            raise RuntimeError("Admin interface is disabled")
        
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        return create_admin_app(self.orchestrator)


# Factory function for creating production service
def create_production_service(
    config: Optional[OrchestrationConfig] = None,
    ai_client_factory=None
) -> ProductionOrchestrationService:
    """Create a production orchestration service."""
    return ProductionOrchestrationService(config, ai_client_factory)