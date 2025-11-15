-- database_security.sql
-- Bonus-specific security configurations

-- Row Level Security (RLS) for bonus tables
ALTER TABLE referral_bonuses ENABLE ROW LEVEL SECURITY;
ALTER TABLE bonus_payout_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE referral_network ENABLE ROW LEVEL SECURITY;

-- Create security policies
CREATE POLICY bonus_select_policy ON referral_bonuses 
    FOR SELECT USING (true);
    
CREATE POLICY bonus_insert_policy ON referral_bonuses 
    FOR INSERT WITH CHECK (current_user IN ('app_user', 'bonus_engine'));
    
CREATE POLICY bonus_update_policy ON referral_bonuses 
    FOR UPDATE USING (current_user IN ('bonus_engine', 'admin_user'));

-- Secure function for bonus calculations
CREATE OR REPLACE FUNCTION calculate_secure_bonus(
    p_purchase_amount DECIMAL(12,2),
    p_level INTEGER,
    p_bonus_percentage DECIMAL(5,4)
) RETURNS DECIMAL(12,2) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_bonus_amount DECIMAL(12,2);
BEGIN
    -- Input validation
    IF p_purchase_amount <= 0 OR p_level < 1 OR p_level > 20 THEN
        RETURN 0;
    END IF;
    
    -- Secure calculation with bounds checking
    v_bonus_amount := p_purchase_amount * GREATEST(0, LEAST(p_bonus_percentage, 1));
    
    -- Apply security limits
    v_bonus_amount := LEAST(v_bonus_amount, 10000000); -- 10M max
    
    RETURN ROUND(v_bonus_amount, 2);
END;
$$;

-- Audit trigger for bonus modifications
CREATE OR REPLACE FUNCTION audit_bonus_changes() 
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO bonus_audit_log (
        bonus_id, old_status, new_status, old_amount, new_amount,
        changed_by, change_reason, ip_address
    ) VALUES (
        COALESCE(NEW.id, OLD.id),
        OLD.status,
        NEW.status,
        OLD.amount,
        NEW.amount,
        current_user,
        TG_OP,
        inet_client_addr()
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bonus_audit_trigger
    AFTER UPDATE ON referral_bonuses
    FOR EACH ROW EXECUTE FUNCTION audit_bonus_changes();