try:
    from drf_yasg import openapi
except ImportError:
    openapi = None


if openapi is None:
    GENERIC_OBJECT_SCHEMA = None
    GENERIC_OBJECT_LIST_SCHEMA = None

    def counted_response_schema(result_key="result"):
        return None

    def wrapped_list_response_schema(result_key):
        return None

    def counted_status_response_schema(result_key="result"):
        return None

    login_request_schema = None
    login_response_schema = None
    company_owner_schema = None
    company_create_request_schema = None
    store_nested_write_schema = None
    order_goods_item_schema = None
    order_write_schema = None
    goods_issue_write_schema = None
    delete_goods_by_user_request_schema = None
    message_response_schema = None
    delete_order_request_schema = None
    delete_order_response_schema = None
else:
    GENERIC_OBJECT_SCHEMA = openapi.Schema(type=openapi.TYPE_OBJECT)
    GENERIC_OBJECT_LIST_SCHEMA = openapi.Schema(
        type=openapi.TYPE_ARRAY,
        items=GENERIC_OBJECT_SCHEMA,
    )


    def counted_response_schema(result_key="result"):
        return openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                result_key: GENERIC_OBJECT_LIST_SCHEMA,
            },
        )


    def wrapped_list_response_schema(result_key):
        return openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                result_key: GENERIC_OBJECT_LIST_SCHEMA,
            },
        )


    def counted_status_response_schema(result_key="result"):
        return openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                "status": openapi.Schema(type=openapi.TYPE_INTEGER),
                result_key: GENERIC_OBJECT_LIST_SCHEMA,
            },
        )


    login_request_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["username", "password"],
        properties={
            "username": openapi.Schema(type=openapi.TYPE_STRING),
            "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
        },
    )


    login_response_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "data": openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "expiry": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                    "token": openapi.Schema(type=openapi.TYPE_STRING),
                    "user": GENERIC_OBJECT_SCHEMA,
                },
            )
        },
    )


    company_owner_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=[
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "email",
            "password",
        ],
        properties={
            "username": openapi.Schema(type=openapi.TYPE_STRING),
            "first_name": openapi.Schema(type=openapi.TYPE_STRING),
            "last_name": openapi.Schema(type=openapi.TYPE_STRING),
            "phone_number": openapi.Schema(type=openapi.TYPE_STRING),
            "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
            "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
        },
    )


    company_create_request_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["company_name", "company_location", "owner"],
        properties={
            "company_name": openapi.Schema(type=openapi.TYPE_STRING),
            "company_location": openapi.Schema(type=openapi.TYPE_STRING),
            "company_tin": openapi.Schema(type=openapi.TYPE_STRING),
            "owner": company_owner_schema,
        },
    )


    store_nested_write_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["store"],
        properties={
            "store": openapi.Schema(
                type=openapi.TYPE_OBJECT,
                required=["store_name", "company", "store_location", "store_supervisor"],
                properties={
                    "store_name": openapi.Schema(type=openapi.TYPE_STRING),
                    "company": openapi.Schema(type=openapi.TYPE_STRING),
                    "store_location": openapi.Schema(type=openapi.TYPE_STRING),
                    "store_supervisor": openapi.Schema(type=openapi.TYPE_STRING),
                },
            )
        },
    )


    order_goods_item_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["goods", "goods_quantity", "price"],
        properties={
            "goods": openapi.Schema(type=openapi.TYPE_INTEGER),
            "goods_quantity": openapi.Schema(type=openapi.TYPE_INTEGER),
            "price": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
        },
    )


    order_write_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "order_caption": openapi.Schema(type=openapi.TYPE_STRING),
            "customer": openapi.Schema(type=openapi.TYPE_INTEGER),
            "customer_name": openapi.Schema(type=openapi.TYPE_STRING),
            "order_discount": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
            "authorization_status": openapi.Schema(type=openapi.TYPE_STRING),
            "order_goods": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=order_goods_item_schema,
            ),
        },
    )


    goods_issue_write_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["goods_issue"],
        properties={
            "goods_issue": openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "issued_status": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "goods_quantity": openapi.Schema(type=openapi.TYPE_INTEGER),
                },
            )
        },
    )


    delete_goods_by_user_request_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["user_id"],
        properties={
            "user_id": openapi.Schema(type=openapi.TYPE_INTEGER),
        },
    )


    message_response_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "message": openapi.Schema(type=openapi.TYPE_STRING),
        },
    )


    delete_order_request_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["order_no"],
        properties={
            "order_no": openapi.Schema(type=openapi.TYPE_INTEGER),
        },
    )


    delete_order_response_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "order_no": openapi.Schema(type=openapi.TYPE_INTEGER),
            "deleted_by": openapi.Schema(type=openapi.TYPE_INTEGER),
            "delete_response": openapi.Schema(type=openapi.TYPE_STRING),
        },
    )
