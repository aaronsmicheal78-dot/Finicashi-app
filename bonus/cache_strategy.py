from redis import Redis
import pickle
from bonus.refferral_tree import ReferralTreeHelper

class ReferralCache:
    """Cache frequently accessed referral data"""
    
    def __init__(self):
        self.redis = Redis(host='localhost', port=6379, db=0)
    
    def get_ancestors_cached(self, user_id: int) -> List[Dict]:
        cache_key = f"ancestors:{user_id}"
        cached = self.redis.get(cache_key)
        
        if cached:
            return pickle.loads(cached)
        
        # Cache miss - compute and store
        ancestors = ReferralTreeHelper.get_ancestors_optimized(user_id)
        self.redis.setex(cache_key, 300, pickle.dumps(ancestors))  # 5 min cache
        return ancestors