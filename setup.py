from setuptools import setup

setup(name='pyjbox',
      version='1.0',
      description='jBox downloader with multiple threads and resume from break point support!',
      url='http://github.com/hebingchang/pyjbox',
      author='hebingchang',
      author_email='hebingchang@sjtu.edu.cn',
      license='MIT',
      packages=['pyjbox'],
      install_requires=[  # 依赖列表
            'requests'
      ],
      zip_safe=False,
      entry_points={
            'console_scripts': ['pyjbox=pyjbox.command_line:main'],
      }
)