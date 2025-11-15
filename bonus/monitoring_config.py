# monitoring_config.py
from datetime import datetime, timedelta
from flask import current_app
import statistics

class BonusMonitoring:
    """Production monitoring for bonus engine"""
    
    def __init__(self):
        self.metrics = {
            'processing_times': [],
            'success_rates': [],
            'error_rates': [],
            'bonus_amounts': [],
            'threat_levels': []
        }
    
    def record_processing_metrics(self, security_context: Dict):
        """Record processing metrics for monitoring"""
        processing_time = security_context.get('processing_duration', 0)
        success = 'error' not in security_context
        
        self.metrics['processing_times'].append(processing_time)
        self.metrics['success_rates'].append(1 if success else 0)
        self.metrics['threat_levels'].append(
            {'low': 0, 'medium': 1, 'high': 2}[security_context.get('threat_level', 'low')]
        )
        
        # Keep only last 1000 records
        for key in self.metrics:
            if len(self.metrics[key]) > 1000:
                self.metrics[key] = self.metrics[key][-1000:]
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate system health report"""
        if not self.metrics['processing_times']:
            return {'status': 'no_data'}
        
        avg_processing_time = statistics.mean(self.metrics['processing_times'])
        success_rate = statistics.mean(self.metrics['success_rates'])
        
        # Calculate threat level distribution
        threat_counts = {
            'low': self.metrics['threat_levels'].count(0),
            'medium': self.metrics['threat_levels'].count(1),
            'high': self.metrics['threat_levels'].count(2)
        }
        
        health_status = 'healthy'
        if success_rate < 0.95:
            health_status = 'degraded'
        if success_rate < 0.90:
            health_status = 'unhealthy'
        
        return {
            'status': health_status,
            'avg_processing_time_seconds': avg_processing_time,
            'success_rate': success_rate,
            'total_processes': len(self.metrics['processing_times']),
            'threat_level_distribution': threat_counts,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def check_anomalies(self) -> List[Dict[str, Any]]:
        """Check for anomalous patterns"""
        anomalies = []
        
        # Check for sudden increase in processing time
        if len(self.metrics['processing_times']) >= 10:
            recent_times = self.metrics['processing_times'][-10:]
            avg_recent = statistics.mean(recent_times)
            avg_historical = statistics.mean(self.metrics['processing_times'][:-10])
            
            if avg_recent > avg_historical * 2:  # 100% increase
                anomalies.append({
                    'type': 'processing_time_spike',
                    'current_avg': avg_recent,
                    'historical_avg': avg_historical,
                    'severity': 'high'
                })
        
        # Check for success rate drop
        if len(self.metrics['success_rates']) >= 20:
            recent_success = statistics.mean(self.metrics['success_rates'][-10:])
            historical_success = statistics.mean(self.metrics['success_rates'][:-10])
            
            if recent_success < historical_success * 0.8:  # 20% drop
                anomalies.append({
                    'type': 'success_rate_drop',
                    'current_rate': recent_success,
                    'historical_rate': historical_success,
                    'severity': 'medium'
                })
        
        return anomalies

# Initialize monitoring
bonus_monitoring = BonusMonitoring()