#!/usr/bin/env python3
from textwrap import dedent
import asyncio
import caproto as ca
from caproto import ChannelType
from caproto.asyncio.client import Context
from caproto.server import PVGroup, ioc_arg_parser, pvproperty, run


class MirrorClientIOC(PVGroup):
    """
    An IOC which mirrors the value, timestamp, and alarm status of a given PV
    into the `mirrored` pvproperty.

    With the default configuration, this IOC assumes that the PV "simple:A"
    exists on some external IOC.

    The "simple" IOC may be started before or after this IOC.  If the server
    goes down, the client will automatically reconnect when available.

    Scalar PVs
    ----------
    mirrored (float, analog input)
    """

    mirrored0 = pvproperty(value=0.0,name='MR1L0',dtype=float)
    mirrored1 = pvproperty(value=0.0,name='MR2L0',dtype=float)
    calculated = pvproperty(value=0.0,name='SUM',dtype=float)

    def __init__(self, pv_to_mirror, *args, **kwargs):
        #self.pv_dict = {"MR1L0:HOMS:MMS:PITCH.RBV": self.mirrored0,
        #    "MR2L0:HOMS:MMS:PITCH.RBV": self.mirrored1
        #    }

        #self.pv_to_mirror = self.pv_dict.keys()
        super().__init__(*args, **kwargs)
        self.pv_dict = {"MR1L0:HOMS:MMS:PITCH.RBV": self.mirrored0,
            "MR2L0:HOMS:MMS:PITCH.RBV": self.mirrored1
            }

                
        self.pv_to_mirror = self.pv_dict.keys()

    async def calculate(self, queue):
      
        ctx = Context()

        while True:
            #pitch_sum = self.mirrored0.read(data_type=ChannelType.DOUBLE).data + self.mirrored1.read(data_type=ChannelType.DOUBLE).data
            m1, m2 = await ctx.get_pvs("mirror:MR1L0","mirror:MR2L0")
            res0 = await m1.read(data_type=ChannelType.DOUBLE)
            res1 = await m2.read(data_type=ChannelType.DOUBLE)
            print(res0.data)
            await asyncio.sleep(1)
            await self.calculated.write(res0.data+res1.data)
            #await queue.put(pitch_sum)

    async def monitor(self, queue):
        # Create an asyncio client context:
        ctx = Context()

        # Loop and grab items from the queue one at a time
        async for event, context, data in ctx.monitor(*self.pv_to_mirror):
            if event == 'subscription':
                print('* Client pushed a new value in the queue')
                print(f'\tValue={data.data} {data.metadata}')
               
                print(context.pv.name)
                #print(self.pv_dict[context.pv.name])
                # Mirror the value, status, severity, and timestamp:

                #await self.mirrored0.write(data.data,
                await self.pv_dict[context.pv.name].write(data.data,
                                          timestamp=data.metadata.timestamp,
                                          status=data.metadata.status,
                                          severity=data.metadata.severity)
            elif event == 'connection':
                print(f'* Client connection state changed: {data}')
                if data == 'disconnected':
                    # Raise an alarm - our client PV is disconnected.
                    await self.pv_dict[context].write(
                        self.pv_dict[context].value,
                        status=ca.AlarmStatus.LINK,
                        severity=ca.AlarmSeverity.MAJOR_ALARM
                    )
            queue.put(None)


    async def __ainit__(self, async_lib):
        print('* `__ainit__` startup hook called')

        queue = asyncio.Queue() 
        await asyncio.gather(
                self.monitor(queue), self.calculate(queue))

        ## Create an asyncio client context:
        #ctx = Context()

        ## Loop and grab items from the queue one at a time
        #async for event, context, data in ctx.monitor(*self.pv_to_mirror):
        #    if event == 'subscription':
        #        print('* Client pushed a new value in the queue')
        #        print(f'\tValue={data.data} {data.metadata}')
        #       
        #        print(context.pv.name)
        #        #print(self.pv_dict[context.pv.name])
        #        # Mirror the value, status, severity, and timestamp:

        #        #await self.mirrored0.write(data.data,
        #        await self.pv_dict[context.pv.name].write(data.data,
        #                                  timestamp=data.metadata.timestamp,
        #                                  status=data.metadata.status,
        #                                  severity=data.metadata.severity)
        #    elif event == 'connection':
        #        print(f'* Client connection state changed: {data}')
        #        if data == 'disconnected':
        #            # Raise an alarm - our client PV is disconnected.
        #            await self.pv_dict[context].write(
        #                self.pv_dict[context].value,
        #                status=ca.AlarmStatus.LINK,
        #                severity=ca.AlarmSeverity.MAJOR_ALARM
        #            )


if __name__ == '__main__':
    ioc_options, run_options = ioc_arg_parser(
        default_prefix='mirror:',
        desc=dedent(MirrorClientIOC.__doc__),
        supported_async_libs=('asyncio', ),
    )

    ioc = MirrorClientIOC('simple:A', **ioc_options)
    run(ioc.pvdb, startup_hook=ioc.__ainit__, **run_options)
