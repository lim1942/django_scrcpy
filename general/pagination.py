from rest_framework.pagination import PageNumberPagination

class SizePageNumberPagination(PageNumberPagination):
    page_size_query_param = 'size'
    max_page_size = 20
