"""
Generates a variety of Dockerfiles based on an input matrix
"""
import os
import shutil
from textwrap import dedent
from ..docker import DockerBuildPack

class LegacyBinderDockerBuildPack(DockerBuildPack):

    dockerfile = '._binder.Dockerfile'

    dockerfile_prependix = dedent(r"""
    COPY python3.frozen.yml /tmp/python3.frozen.yml
    COPY root.frozen.yml /tmp/root.frozen.yml
    # update conda in two steps because the base image
    # has very old conda that can't upgrade past 4.3
    RUN conda install -yq conda>=4.3 && \
        conda install -yq conda==4.4.11 && \
        conda env update -n python3 -f /tmp/python3.frozen.yml && \
        conda remove -yq -n python3 nb_conda_kernels && \
        conda env update -n root -f /tmp/root.frozen.yml && \
        /home/main/anaconda2/envs/python3/bin/ipython kernel install --sys-prefix && \
        /home/main/anaconda2/bin/ipython kernel install --prefix=/home/main/anaconda2/envs/python3 && \
        /home/main/anaconda2/bin/ipython kernel install --sys-prefix
    """)

    dockerfile_appendix = dedent(r"""
    USER root
    COPY . /home/main/notebooks
    RUN chown -R main:main /home/main/notebooks && \
        rm /home/main/notebooks/root.frozen.yml && \
        rm /home/main/notebooks/python3.frozen.yml
    USER main
    WORKDIR /home/main/notebooks
    ENV PATH /home/main/anaconda2/envs/python3/bin:$PATH
    ENV JUPYTER_PATH /home/main/anaconda2/share/jupyter:$JUPYTER_PATH
    CMD jupyter notebook --ip 0.0.0.0
    """)

    def render(self):
        segments = [
            'FROM andrewosh/binder-base@sha256:eabde24f4c55174832ed8795faa40cea62fc9e2a4a9f1ee1444f8a2e4f9710ee',
            self.dockerfile_prependix,
        ]
        with open('Dockerfile') as f:
            for line in f:
                if line.strip().startswith('FROM'):
                    break
            segments.append(f.read())
        segments.append(self.dockerfile_appendix)
        return '\n'.join(segments)

    def get_build_script_files(self):
       return {
            'legacy/root.frozen.yml': '/tmp/root.frozen.yml',
            'legacy/python3.frozen.yml': '/tmp/python3.frozen.yml',
        }
            
    def build(self, image_spec, memory_limit, build_args):
        with open(self.dockerfile, 'w') as f:
            f.write(self.render())
        for env in ('root', 'python3'):
            env_file = env + '.frozen.yml'
            src_path = os.path.join(
                os.path.dirname(__file__),
                env_file,
            )
            shutil.copy(src_path, env_file)
        return super().build(image_spec, memory_limit, build_args)

    def detect(self):
        try:
            with open('Dockerfile', 'r') as f:
                for line in f:
                    if line.startswith('FROM'):
                        if 'andrewosh/binder-base' in line.split('#')[0].lower():
                            return True
                        else:
                            return False
        except FileNotFoundError:
            pass

        return False
