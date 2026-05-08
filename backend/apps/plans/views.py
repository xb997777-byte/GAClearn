from rest_framework.views import APIView

from common.permissions import IsWxAuthenticated
from common.responses import error_response, success_response

from .serializers import (
    PlanApplyAIPatchSerializer,
    PlanCreateSerializer,
    PlanRollbackSerializer,
    PlanUpdateSerializer,
    SwitchBookSerializer,
)
from .services import (
    apply_ai_plan_patch,
    build_today_task_payload,
    create_plan,
    get_manageable_plan,
    list_plan_revisions,
    mark_today_task_finished,
    mark_today_task_started,
    rollback_plan_revision,
    serialize_plan,
    switch_book,
    update_current_plan,
)


class CurrentPlanView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(serialize_plan(get_manageable_plan(request.user)))

    def put(self, request):
        serializer = PlanUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            plan = update_current_plan(request.user, serializer.validated_data)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response(serialize_plan(plan), message="plan updated")


class PlanCreateView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = PlanCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            plan = create_plan(request.user, **serializer.validated_data)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response(serialize_plan(plan), message="plan created", status_code=201)


class SwitchBookView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = SwitchBookSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            plan = switch_book(request.user, **serializer.validated_data)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response(serialize_plan(plan), message="book switched")


class TodayTaskView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(build_today_task_payload(request.user))


class TodayTaskStartView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        try:
            task = mark_today_task_started(request.user)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response({"task_id": task.id}, message="today task started")


class TodayTaskFinishView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        try:
            task = mark_today_task_finished(request.user)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response({"task_id": task.id}, message="today task finished")


class CurrentPlanHistoryView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        limit = request.query_params.get("limit", 12)
        return success_response({"list": list_plan_revisions(request.user, limit=limit)})


class CurrentPlanApplyAIPatchView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = PlanApplyAIPatchSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            plan = apply_ai_plan_patch(
                request.user,
                serializer.validated_data["patch"],
                summary=serializer.validated_data.get("summary", ""),
                metadata={"evidence": serializer.validated_data.get("evidence", {})},
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response(serialize_plan(plan), message="ai patch applied")


class CurrentPlanRollbackView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = PlanRollbackSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            plan = rollback_plan_revision(request.user, serializer.validated_data["revision_id"])
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response(serialize_plan(plan), message="plan rolled back")
