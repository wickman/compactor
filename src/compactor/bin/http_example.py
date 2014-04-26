import compactor
from compactor import route
from compactor.process import Process


import logging
logging.basicConfig()


class WebProcess(Process):
  def __init__(self):
    super(WebProcess, self).__init__('web')

  @route('/vars')
  def vars(self, handler):
    handler.write('These are my vars')


def main():
  compactor.initialize()
  
  process = WebProcess()
  compactor.spawn(process)
  
  compactor.join()


if __name__ == '__main__':
  main()
