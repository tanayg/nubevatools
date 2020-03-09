FROM alpine


RUN apk update && apk add wget && apk add bash
RUN mkdir /opt/nubevaTools
RUN wget -O /opt/nubevaTools/loadGenerateAWS.sh https://raw.githubusercontent.com/nubevalabs/NubevaTools/master/loadGenerateAWS.sh
RUN chmod +x /opt/nubevaTools/loadGenerateAWS.sh
WORKDIR /opt/nubevaTools

CMD /opt/nubevaTools/loadGenerateAWS.sh
