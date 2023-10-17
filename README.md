# only_prometheus_exporter
## One exporter to rule them all - Universal metrics exporter for prometheus

I got bored of setting up multiple exporters and configuring multi port access im my firewall for each server so I consolidated all 
metrics that I need into one exporter.

* Feel free to leave an issue if something you need is missing
* Make a pull request if you implemented some update that others could benefit from.
* Writen in python because that is what I know best :)
* Philosophy for label usage is better to have redundancy, than to mess around with joins later

### ToDo:
- [X] Support nvidia gpu metrics
- [X] Support filesystem metrics
- [X] Support CPU metrics
- [ ] Support network metrics
- [X] Support memory metrics
- [X] Support host metrics
- [ ] Support docker metrics
- [ ] Provide example grafana dashboard
- [X] Create builds to remove need to install packages
- [ ] Allow installation using apt
- [ ] Verify support for non-linux systems
- [X] Support linux screen metrics
- [ ] Add config options
  - [ ] Basic auth
  - [ ] SSL
  - [ ] Port
  - [ ] Host