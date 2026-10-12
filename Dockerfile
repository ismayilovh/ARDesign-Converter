FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt --fix-broken install -y \
    && apt install -y python3.11 python3 git git-lfs python3-wheel python3.11-venv \
    && apt install -y xvfb

WORKDIR /app/blender-git
#TODO: try --recursive-submodules
RUN git clone https://projects.blender.org/blender/blender.git

WORKDIR blender
#TODO: try to install a specific version e.g. run git checkout 4.3.2
RUN apt update && apt install -y build-essential git git-lfs subversion cmake libx11-dev libxxf86vm-dev libxcursor-dev libxi-dev libxrandr-dev libxinerama-dev libegl-dev \
    && apt install -y libwayland-dev wayland-protocols libxkbcommon-dev libdbus-1-dev linux-libc-dev

RUN make update && make -j$(nproc) bpy

RUN apt-get install python3-setuptools

RUN python3 build_files/utils/make_bpy_wheel.py ../build_linux_bpy/bin/ --output-dir=./

WORKDIR /app/converter

RUN python3.11 -m venv venv && . venv/bin/activate && cd .. && cd blender-git && cd blender \
    && apt install -y python3-pip && python3 -m pip install *.whl

WORKDIR /app/freecad-git

RUN git clone --recurse-submodules https://github.com/FreeCAD/FreeCAD.git

WORKDIR FreeCAD

RUN git checkout 1.0.0 -f && apt-get update && apt install -y cmake cmake-gui \ 
    libboost-date-time-dev libboost-dev libboost-filesystem-dev \ 
    libboost-graph-dev libboost-iostreams-dev libboost-program-options-dev \
    libboost-python-dev libboost-regex-dev libboost-serialization-dev \ 
    libboost-thread-dev libcoin-dev libeigen3-dev libgts-bin libgts-dev \
    libkdtree++-dev libmedc-dev libocct-data-exchange-dev libocct-ocaf-dev \
    libocct-visualization-dev libopencv-dev libproj-dev libpyside2-dev \
    libqt5opengl5-dev libqt5svg5-dev qtwebengine5-dev libqt5x11extras5-dev \
    libqt5xmlpatterns5-dev libshiboken2-dev libspnav-dev libvtk9-dev \
    libx11-dev libxerces-c-dev libzipios++-dev occt-draw \
    pyside2-tools python3-dev python3-matplotlib python3-packaging \
    python3-pivy python3-ply python3-pyside2.qtcore python3-pyside2.qtgui \
    python3-pyside2.qtsvg python3-pyside2.qtwidgets python3-pyside2.qtnetwork \
    python3-pyside2.qtwebengine python3-pyside2.qtwebenginecore \ 
    python3-pyside2.qtwebenginewidgets python3-pyside2.qtwebchannel python3-markdown \
    python3-git qtbase5-dev qttools5-dev swig libyaml-cpp-dev \
    && mkdir build

WORKDIR build

RUN cmake ../ -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local && make -j$(nproc) && make install

WORKDIR /app/converter

COPY . /app/converter/

ENTRYPOINT ["xvfb-run","-a","/venv/bin/python3.11","test.py"]