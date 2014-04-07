python_test_suite(
  name = 'all',
  dependencies = [
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
