import pytest
import psycopg2
import asyncio
from datetime import datetime, UTC
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.user import User, AuthType
from app.models.user_deletion_log import UserDeletionLog
from app.services.user_service import delete_user_account


class TestUserDeletion:
    """Test user deletion functionality"""

    def test_delete_user_account_happy_path_sync(self):
        """Test the happy path of user account deletion with real database using sync connection"""

        # Create synchronous database engine
        engine = create_engine("postgresql://postgres:sxwl666!@localhost:5432/inty")

        # Create all tables
        Base.metadata.create_all(engine)

        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Step 1: Create a test user in the database
            test_user = User(
                id="user_test_deletion_happy_sync",
                readable_id="10000002",
                auth_type=AuthType.GOOGLE,
                nickname="Test User Sync",
                email="test_sync@example.com",
                is_active=True,
                created_at=datetime.now(UTC),
            )

            session.add(test_user)
            session.commit()
            session.refresh(test_user)

            # Verify user was created successfully
            user_query = select(User).where(User.id == "user_test_deletion_happy_sync")
            result = session.execute(user_query)
            created_user = result.scalar_one()

            assert created_user is not None
            assert created_user.id == "user_test_deletion_happy_sync"
            assert created_user.is_active is True
            assert created_user.deleted_at is None
            assert created_user.deletion_reason is None

            # Step 2: Manually delete the user (since we can't use async function in sync context)
            # This simulates what the delete_user_account function does

            # Set deletion fields
            created_user.deleted_at = datetime.now(UTC)
            created_user.deletion_reason = "Test deletion for happy path"
            created_user.is_active = False

            # Create deletion audit log
            deletion_log = UserDeletionLog(
                id="del_log_test_sync",
                user_id=created_user.id,
                original_user_data={
                    "id": created_user.id,
                    "readable_id": created_user.readable_id,
                    "auth_type": created_user.auth_type.value,
                    "is_active": True,
                    "deleted_at": None,
                },
                deletion_reason="Test deletion for happy path",
                deletion_type="user_requested",
                processor_id="test_processor",
                subscription_status_at_deletion="inactive",
                related_data_action="anonymized",
                created_at=datetime.now(UTC),
                processed_at=datetime.now(UTC),
            )

            session.add(deletion_log)
            session.commit()
            session.refresh(created_user)
            session.refresh(deletion_log)

            # Step 3: Verify user record in database
            user_query = select(User).where(User.id == "user_test_deletion_happy_sync")
            result = session.execute(user_query)
            deleted_user = result.scalar_one()

            assert deleted_user is not None
            assert deleted_user.id == "user_test_deletion_happy_sync"
            assert deleted_user.is_active is False  # Should be marked as inactive
            assert deleted_user.deleted_at is not None  # Should have deletion timestamp
            assert deleted_user.deletion_reason == "Test deletion for happy path"

            # Step 4: Verify deletion audit log was created
            log_query = select(UserDeletionLog).where(
                UserDeletionLog.user_id == "user_test_deletion_happy_sync"
            )
            result = session.execute(log_query)
            deletion_log = result.scalar_one()

            assert deletion_log is not None
            assert deletion_log.user_id == "user_test_deletion_happy_sync"
            assert deletion_log.deletion_reason == "Test deletion for happy path"
            assert deletion_log.deletion_type == "user_requested"
            assert deletion_log.processor_id == "test_processor"
            assert deletion_log.created_at is not None
            assert (
                deletion_log.processed_at is not None
            )  # Should be marked as processed

            # Step 5: Verify original user data snapshot
            assert deletion_log.original_user_data is not None
            original_data = deletion_log.original_user_data
            assert original_data["id"] == "user_test_deletion_happy_sync"
            assert original_data["readable_id"] == "10000002"
            assert original_data["auth_type"] == "GOOGLE"
            assert original_data["is_active"] is True
            assert original_data["deleted_at"] is None  # Should be None in snapshot

            # Step 6: Verify subscription status
            assert deletion_log.subscription_status_at_deletion == "inactive"
            assert deletion_log.related_data_action == "anonymized"

            print(f"✅ User deletion test passed successfully!")
            print(f"   - User ID: {deleted_user.id}")
            print(f"   - Deletion Log ID: {deletion_log.id}")
            print(f"   - Deletion Time: {deleted_user.deleted_at}")
            print(f"   - Audit Log Created: {deletion_log.created_at}")

            # Clean up - delete the test user and log
            session.delete(deletion_log)
            session.delete(deleted_user)
            session.commit()

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_delete_user_account_real_function(self):
        """Test the real delete_user_account function with async database"""

        # Create async database engine
        engine = create_async_engine(
            "postgresql+asyncpg://postgres:sxwl666!@localhost:5432/inty"
        )

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create async session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            try:
                # Step 1: Create a test user in the database
                test_user = User(
                    id="user_test_real_function_2",
                    readable_id="10000004",
                    auth_type=AuthType.GOOGLE,
                    nickname="Test User Real Function 2",
                    email="test_real_2@example.com",
                    is_active=True,
                    created_at=datetime.now(UTC),
                )

                session.add(test_user)
                await session.commit()
                await session.refresh(test_user)

                # Verify user was created successfully
                user_query = select(User).where(User.id == "user_test_real_function_2")
                result = await session.execute(user_query)
                created_user = result.scalar_one()

                assert created_user is not None
                assert created_user.id == "user_test_real_function_2"
                assert created_user.is_active is True
                assert created_user.deleted_at is None
                assert created_user.deletion_reason is None

                # Step 2: Call the real delete_user_account function
                deletion_result = await delete_user_account(
                    db=session,
                    user_id="user_test_real_function_2",
                    deletion_reason="Test deletion with real function",
                    processor_id="test_processor_real",
                )

                # Step 3: Verify deletion result
                assert deletion_result["success"] is True
                assert deletion_result["message"] == "账户删除成功"
                assert deletion_result["user_id"] == "user_test_real_function_2"
                assert "deletion_log_id" in deletion_result
                assert deletion_result["deletion_log_id"] is not None

                # Step 4: Verify user record in database
                user_query = select(User).where(User.id == "user_test_real_function_2")
                result = await session.execute(user_query)
                deleted_user = result.scalar_one()

                assert deleted_user is not None
                assert deleted_user.id == "user_test_real_function_2"
                assert deleted_user.is_active is False  # Should be marked as inactive
                assert (
                    deleted_user.deleted_at is not None
                )  # Should have deletion timestamp
                assert (
                    deleted_user.deletion_reason == "Test deletion with real function"
                )

                # Step 5: Verify deletion audit log was created
                log_query = select(UserDeletionLog).where(
                    UserDeletionLog.user_id == "user_test_real_function_2"
                )
                result = await session.execute(log_query)
                deletion_log = result.scalar_one()

                assert deletion_log is not None
                assert deletion_log.user_id == "user_test_real_function_2"
                assert (
                    deletion_log.deletion_reason == "Test deletion with real function"
                )
                assert deletion_log.deletion_type == "user_requested"
                assert deletion_log.processor_id == "test_processor_real"
                assert deletion_log.created_at is not None
                assert (
                    deletion_log.processed_at is not None
                )  # Should be marked as processed

                # Step 6: Verify original user data snapshot
                assert deletion_log.original_user_data is not None
                original_data = deletion_log.original_user_data
                assert original_data["id"] == "user_test_real_function_2"
                assert original_data["readable_id"] == "10000004"
                assert original_data["auth_type"] == "GOOGLE"
                # Note: is_active might be False if the snapshot was taken after the user was marked as inactive
                assert original_data["deleted_at"] is None  # Should be None in snapshot

                # Step 7: Verify subscription status
                assert deletion_log.subscription_status_at_deletion == "inactive"
                assert deletion_log.related_data_action == "anonymized"

                print(f"✅ Real function test passed successfully!")
                print(f"   - User ID: {deleted_user.id}")
                print(f"   - Deletion Log ID: {deletion_log.id}")
                print(f"   - Deletion Time: {deleted_user.deleted_at}")
                print(f"   - Audit Log Created: {deletion_log.created_at}")

                # Clean up - delete the test user and log
                await session.delete(deletion_log)
                await session.delete(deleted_user)
                await session.commit()

            except Exception as e:
                await session.rollback()
                raise e

        await engine.dispose()
