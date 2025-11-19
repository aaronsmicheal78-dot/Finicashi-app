# Run this in your Python shell
from extensions import db
from models import ReferralBonus, User

bonuses = ReferralBonus.query.filter_by(payment_id=148).all()
print(f"Found {len(bonuses)} bonuses for payment 148")
for b in bonuses:
    user = User.query.get(b.user_id)
    print(f"User {user.username}: Level {b.level} - UGX {b.amount} - Status: {b.status}")



 @app.route('/debug/referral-network')
    def debug_referral_network_route():
         """Debug route to check referral network structure"""
     
        
         debug_output = []
         debug_output.append("🔍 REFERRAL NETWORK STRUCTURE:")
        
         try:
            # Check all relationships for user 19
            user_19_relationships = db.session.execute(
                text("""
                    SELECT * FROM referral_network 
                    WHERE ancestor_id = 19 OR descendant_id = 19
                    ORDER BY depth
                """)
            ).fetchall()
            
            debug_output.append(f"User 19 relationships:")
            for rel in user_19_relationships:
                debug_output.append(f"  Ancestor: {rel.ancestor_id} -> Descendant: {rel.descendant_id}, Depth: {rel.depth}")
            
            # Check the entire network structure
            all_relationships = db.session.execute(
                text("""
                    SELECT ancestor_id, descendant_id, depth 
                    FROM referral_network 
                    WHERE depth > 0
                    ORDER BY descendant_id, depth
                    LIMIT 20
                """)
            ).fetchall()
            
            debug_output.append("Sample of all relationships (depth > 0):")
            for rel in all_relationships:
                ancestor = User.query.get(rel.ancestor_id)
                descendant = User.query.get(rel.descendant_id)
                ancestor_name = ancestor.username if ancestor else 'Unknown'
                descendant_name = descendant.username if descendant else 'Unknown'
                debug_output.append(f"  {ancestor_name} ({rel.ancestor_id}) -> {descendant_name} ({rel.descendant_id}) [Level {rel.depth}]")
            
            return "<br>".join(debug_output)
        
         except Exception as e:
            return f"Error: {str(e)}"
         
    @app.route('/debug/bonus-config')
    def debug_bonus_config():
        """Debug route to verify bonus configuration"""
        output = []
    
        try:
            from decimal import Decimal
            from bonus.bonus_config import bonus_orchestrator, BonusConfigHelper
            from bonus.refferral_tree import ReferralTreeHelper
            output.append("🎯 BONUS CONFIGURATION VERIFICATION")
            output.append("=" * 50)
            
            # Get configuration info
            config_info = bonus_orchestrator.get_bonus_configuration_info()
            config = config_info['configuration']
            
            output.append(f"📊 BONUS DISTRIBUTION (Levels 1-{config['max_level']}):")
            output.append(f"Total Percentage: {config['total_percentage'] * 100:.2f}%")
            output.append("")
            
            # Show each level's percentage
            for level in sorted(config['distribution'].keys()):
                level_info = config['distribution'][level]
                output.append(f"Level {level:2d}: {level_info['percentage_display']:6s} ({level_info['percentage']:.3f})")
            
            output.append("")
            output.append("🧪 VALIDATION:")
            is_valid, message = config_info['validation']
            if is_valid:
                output.append(f"✅ {message}")
            else:
                output.append(f"❌ {message}")
            
            # Test calculation for each level with 100,000 UGX
            output.append("")
            output.append("🧮 SAMPLE CALCULATIONS (100,000 UGX):")
            test_amount = Decimal('100000')
            
            for level in [1, 2, 3, 4, 5, 6, 10, 15, 20]:
                percentage = BonusConfigHelper.get_bonus_percentage(level)
                bonus_amount = test_amount * percentage
                bonus_amount = bonus_amount.quantize(Decimal('0.01'))
                output.append(f"Level {level:2d}: {percentage*100:5.1f}% → {bonus_amount:8,.0f} UGX")
            
            return "<br>".join(output)
            
        except Exception as e:
            return f"❌ Debug failed: {str(e)}"
        
    @app.route('/debug/check-bonus-calculation/<int:payment_id>')
    def check_bonus_calculation(payment_id):
        """Debug route to check bonus calculation results"""
        from flask import jsonify
        from bonus.bonus_calculation import BonusCalculationHelper
    
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return jsonify({'error': 'Payment not found'}), 404
            
            # Calculate bonuses
            success, bonuses, message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
            
            # Validate each bonus
            validation_results = []
            for i, bonus in enumerate(bonuses):
                is_valid, reason = self._basic_bonus_validation_with_reason(bonus)
                validation_results.append({
                    'bonus_index': i,
                    'bonus_data': bonus,
                    'is_valid': is_valid,
                    'validation_reason': reason
                })
            
            return jsonify({
                'payment_id': payment_id,
                'calculation_success': success,
                'calculation_message': message,
                'total_bonuses_calculated': len(bonuses),
                'validation_results': validation_results,
                'audit_info': audit_info
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
   
    @app.route('/debug/user-model')
    def debug_user_model():
        from models import User
        from flask import jsonify
        
        # Get a sample user
        user = User.query.first()
        if not user:
            return jsonify({'error': 'No users found'})
        
        # Get all column names
        columns = [column.name for column in User.__table__.columns]
        
        # Get all attributes (including relationships)
        all_attrs = [attr for attr in dir(user) if not attr.startswith('_')]
        
        # Filter for potential referral fields
        referral_attrs = [attr for attr in all_attrs if any(keyword in attr.lower() for keyword in ['refer', 'sponsor', 'upline', 'parent'])]
        
        return jsonify({
            'columns': columns,
            'all_attributes': all_attrs,
            'referral_attributes': referral_attrs,
            'sample_user': {attr: getattr(user, attr) for attr in columns}
        })
    
    from flask import current_app  # Add this import at the top of your app.py

    @app.route('/debug/validate-bonus-data/<int:payment_id>')
    def debug_validate_bonus_data(payment_id):
        """Debug route to validate bonus data and see exactly what's wrong"""
        from flask import jsonify
        from bonus.bonus_calculation import BonusCalculationHelper
        
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return jsonify({'error': 'Payment not found'}), 404
            
            # Calculate bonuses
            success, bonuses, message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
            
            if not success:
                return jsonify({
                    'payment_id': payment_id,
                    'calculation_success': False,
                    'calculation_message': message,
                    'audit_info': audit_info
                })
            
            # Test validation for each bonus
            validation_results = []
            from bonus.bonus_config import bonus_orchestrator
            
            for i, bonus in enumerate(bonuses):
                # Test basic validation
                is_valid, reason = bonus_orchestrator._basic_bonus_validation_with_reason(bonus)
                
                # Check each field individually
                field_checks = {}
                
                # Check user_id
                user_id = bonus.get('user_id')
                field_checks['user_id'] = {
                    'value': user_id,
                    'valid': isinstance(user_id, int) and user_id > 0,
                    'exists_in_db': User.query.get(user_id) is not None
                }
                
                # Check amount
                amount = bonus.get('amount')
                field_checks['amount'] = {
                    'value': amount,
                    'valid': isinstance(amount, (int, float)) and amount > 0,
                    'type': type(amount).__name__
                }
                
                # Check level
                level = bonus.get('level')
                field_checks['level'] = {
                    'value': level,
                    'valid': isinstance(level, int) and 1 <= level <= 20,
                    'type': type(level).__name__
                }
                
                # Check purchase_id
                purchase_id = bonus.get('purchase_id')
                field_checks['purchase_id'] = {
                    'value': purchase_id,
                    'valid': isinstance(purchase_id, int) and purchase_id > 0,
                    'exists_in_db': Payment.query.get(purchase_id) is not None
                }
                
                validation_results.append({
                    'bonus_index': i,
                    'bonus_data': bonus,
                    'is_valid': is_valid,
                    'validation_reason': reason,
                    'field_checks': field_checks
                })
            
            return jsonify({
                'payment_id': payment_id,
                'calculation_success': success,
                'calculation_message': message,
                'total_bonuses_calculated': len(bonuses),
                'validation_results': validation_results,
                'audit_info': audit_info
            })
            
        except Exception as e:
            current_app.logger.error(f"Error in debug_validate_bonus_data: {str(e)}")
    
  
    @app.route('/debug/check-created-bonuses/<int:payment_id>')
    def check_created_bonuses(payment_id):
        """Check what bonuses have been created for a payment"""
        from flask import jsonify
        
        try:
            # Get all bonuses for this payment
            bonuses = ReferralBonus.query.filter_by(payment_id=payment_id).all()
            
            bonus_list = []
            for bonus in bonuses:
                bonus_list.append({
                    'id': bonus.id,
                    'user_id': bonus.user_id,
                    'level': bonus.level,
                    'amount': float(bonus.amount),
                    'status': bonus.status,
                    'created_at': bonus.created_at.isoformat() if bonus.created_at else None
                })
            
            return jsonify({
                'payment_id': payment_id,
                'total_bonuses_created': len(bonuses),
                'bonuses': bonus_list
            })
            
        except Exception as e:
            current_app.logger.error(f"Error in check_created_bonuses: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/debug/check-referral-bonus-schema')
    def check_referral_bonus_schema():
        """Check the ReferralBonus model structure"""
        from flask import jsonify
        
        try:
            # Get all column names and types
            columns = []
            for column in ReferralBonus.__table__.columns:
                columns.append({
                    'name': column.name,
                    'type': str(column.type),
                    'nullable': column.nullable,
                    'primary_key': column.primary_key
                })
            
            # Try to create a test bonus
            test_bonus = ReferralBonus(
                user_id=1,
                payment_id=1,
                amount=100.0,
                level=1,
                status='pending'
            )
            
            return jsonify({
                'columns': columns,
                'test_bonus_creation': 'success',
                'test_bonus_fields': {column.name: getattr(test_bonus, column.name) for column in ReferralBonus.__table__.columns}
            })
            
        except Exception as e:
            current_app.logger.error(f"Error in check_referral_bonus_schema: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/debug/create-test-referral-chain')
    def create_test_referral_chain():
        """Create a test referral chain for testing bonuses"""
        from flask import jsonify
        
        try:
            # Create test users with referral chain: user1 -> user2 -> user3 -> user4 -> user5
            users = []
            
            # User 1 (root - no referrer)
            user1 = User(
                username='test_root',
                email='root@test.com',
                phone='1111111111',
                referral_code='ROOT123',
                referred_by=None,
                referral_bonus_eligible=True
            )
            user1.set_password('password123')
            users.append(user1)
            
            # User 2 (referred by user1)
            user2 = User(
                username='test_level1',
                email='level1@test.com', 
                phone='2222222222',
                referral_code='LEVEL1',
                referred_by=user1.id,
                referral_bonus_eligible=True
            )
            user2.set_password('password123')
            users.append(user2)
            
            # User 3 (referred by user2)
            user3 = User(
                username='test_level2',
                email='level2@test.com',
                phone='3333333333', 
                referral_code='LEVEL2',
                referred_by=user2.id,
                referral_bonus_eligible=True
            )
            user3.set_password('password123')
            users.append(user3)
            
            # User 4 (referred by user3)
            user4 = User(
                username='test_level3',
                email='level3@test.com',
                phone='4444444444',
                referral_code='LEVEL3', 
                referred_by=user3.id,
                referral_bonus_eligible=True
            )
            user4.set_password('password123')
            users.append(user4)
            
            # User 5 (referred by user4) - This will be the paying user
            user5 = User(
                username='test_paying_user',
                email='paying@test.com',
                phone='5555555555',
                referral_code='PAYING',
                referred_by=user4.id,
                referral_bonus_eligible=True
            )
            user5.set_password('password123')
            users.append(user5)
            
            # Add all users to database
            for user in users:
                db.session.add(user)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Test referral chain created',
                'users': [
                    {'id': user1.id, 'username': user1.username, 'referred_by': user1.referred_by},
                    {'id': user2.id, 'username': user2.username, 'referred_by': user2.referred_by},
                    {'id': user3.id, 'username': user3.username, 'referred_by': user3.referred_by},
                    {'id': user4.id, 'username': user4.username, 'referred_by': user4.referred_by},
                    {'id': user5.id, 'username': user5.username, 'referred_by': user5.referred_by}
                ],
                'referral_chain': 'user1 -> user2 -> user3 -> user4 -> user5'
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in create_test_referral_chain: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/debug/check-user-referral-chain/<int:user_id>')
    def check_user_referral_chain(user_id):
        """Check the referral chain for a specific user"""
        from flask import jsonify

    # @app.route('/debug/process-bonus-payments')
    # @app.route('/debug/process-bonus-payments/<int:user_id>')
    # def debug_process_bonus_payments(user_id=None):
    #         """Debug endpoint to process bonus payments"""
    #         try:
    #             from extensions import db, SessionLocal
    #             result = process_bonus_payments(user_id, db_session)
    #             return jsonify(result)
    #         except Exception as e:
    #             return jsonify({"error": str(e)}), 500

    # def process_bonus_payments(user_id=None, session=None):
    #     """Process bonus payments for a specific user or all users"""
    #     if session is None:
    #         session = db_session
            
    #     try:
    #         # Query for pending bonuses
    #         query = session.query(ReferralBonus).filter(
    #             ReferralBonus.status == 'pending'
    #         )
            
    #         if user_id:
    #             query = query.filter(ReferralBonus.user_id == user_id)
            
    #         pending_bonuses = query.all()
            
    #         payment_results = []
    #         total_paid = 0
            
    #         for bonus in pending_bonuses:
    #             user = session.query(User).filter(User.id == bonus.user_id).first()
    #             if not user:
    #                 continue
                
    #             # Update user balance
    #             if not hasattr(user, 'balance'):
    #                 # Create balance attribute if it doesn't exist
    #                 from sqlalchemy import Column, Numeric
    #                 # You'll need to add this to your User model
    #                 continue
                
    #             old_balance = user.balance if user.balance else 0
    #             user.balance = (user.balance or 0) + bonus.amount
                
    #             # Update bonus status
    #             bonus.status = 'paid'
    #             bonus.paid_at = datetime.utcnow()
                
    #             payment_results.append({
    #                 'user_id': user.id,
    #                 'username': user.username,
    #                 'bonus_id': bonus.id,
    #                 'level': bonus.level,
    #                 'amount': float(bonus.amount),
    #                 'old_balance': float(old_balance),
    #                 'new_balance': float(user.balance),
    #                 'status': 'success'
    #             })
                
    #             total_paid += bonus.amount
            
    #         # Commit the transaction
    #         session.commit()
            
    #         return {
    #             'success': True,
    #             'total_bonuses_paid': len(payment_results),
    #             'total_amount_paid': float(total_paid),
    #             'payments': payment_results
    #         }
            
    #     except Exception as e:
    #         session.rollback()
    #         return {
    #             'success': False,
    #             'error': str(e)
    #         }

        
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        referral_chain = []
        current_user = user
        level = 0
        
        while current_user and level < 20:
            referral_chain.append({
                'level': level,
                'user_id': current_user.id,
                'username': current_user.username,
                'referred_by': current_user.referred_by
            })
            
            if not current_user.referred_by:
                break
                
            current_user = User.query.get(current_user.referred_by)
            level += 1
        
        return jsonify({
            'target_user': {
                'id': user.id,
                'username': user.username,
                'referred_by': user.referred_by
            },
            'referral_chain': referral_chain,
            'chain_length': len(referral_chain) - 1  # Exclude the target user
        })

# Test your specific payment (replace 183 with your payment ID)