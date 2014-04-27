python_test_suite(
  name = 'all',
  dependencies = [
    pants(':test_httpd'),
    pants(':test_process'),
  ]
)


python_tests(
  name = 'test_process',
  sources = ['test_process.py'],
  dependencies = [
    pants('src/compactor'),
  ],
)


python_tests(
  name = 'test_httpd',
  sources = ['test_httpd.py'],
  dependencies = [
    pants('src/compactor'),
    python_requirement('requests'),
  ],
)
