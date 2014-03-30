#!/usr/bin/perl

$MIR='/home/sudomirror/public_html/mirror';

die unless $#ARGV==0;
if ($ARGV[0]=~/^(git|http|https):\/\/(.*?)\/(.*)$/s) {
        $proto = $1;
        $domain = $2;
        $path = $3;
        if ($proto ne 'git') {
                $proto_dir = 'git-'.$proto;
        } else {
                $proto_dir = 'git';
        }
        if ($path=~/^(.*?);(.*)$/s) {
                $path = $1;
                $branch = $2;
        } else {
                $branch = 'master';
        }
        system('mkdir','-p',"$MIR/$proto_dir/$domain/$path");
        chdir ("$MIR/$proto_dir/$domain/$path") or die "$!\n";
        system('git', '--bare', 'init');
        print "[git-clonerepo.pl:] About to fetch.";
        system('git', '--bare', 'fetch', "$proto://$domain/$path", "$branch:$branch");
        system('git','update-server-info');
}

